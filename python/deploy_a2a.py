"""Deploy, grant resource-level IAM on, bind Agent Gateways to, or delete an ADK A2A agent on Agent Runtime.

Usage:
    # Deploy a new A2A agent
    uv run python deploy_a2a.py currency_agent \\
      --project=$PROJECT_ID \\
      --region=$REGION \\
      --display-name=currency-agent \\
      --env MCP_SERVER_NAME=$MCP_SERVER_NAME

    # Grant least-privilege resource-level invoker IAM on an agent
    uv run python deploy_a2a.py \\
      --project=$PROJECT_ID \\
      --region=$REGION \\
      --agent-engine-id=$CURRENCY_AGENT_ENGINE_ID \\
      --grant-invoker="$TRAVEL_AGENT_PRINCIPAL"

    # Bind an egress (and optional ingress) Agent Gateway to an existing agent
    uv run python deploy_a2a.py \\
      --project=$PROJECT_ID \\
      --region=$REGION \\
      --agent-engine-id=$TRAVEL_AGENT_ENGINE_ID \\
      --egress-gateway=travel-agent-egress-gateway

    # Delete an Agent Runtime instance (with force=True)
    uv run python deploy_a2a.py \\
      --project=$PROJECT_ID \\
      --region=$REGION \\
      --agent-engine-id=$TRAVEL_AGENT_ENGINE_ID \\
      --delete
"""

import argparse
import importlib.util
from pathlib import Path
import time

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.protobuf import json_format
import vertexai
from vertexai import types
from vertexai._genai import _agent_engines_utils
from vertexai.agent_engines import _agent_engines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy, update gateways on, or delete an ADK A2A agent on Agent Runtime."
    )
    parser.add_argument(
        "agent_dir",
        nargs="?",
        choices=["currency_agent", "travel_agent"],
        help="Agent package directory to deploy (omit for gateway-only update or --delete).",
    )
    parser.add_argument("--project", required=True, help="Google Cloud project ID.")
    parser.add_argument("--region", required=True, help="Google Cloud region.")
    parser.add_argument(
        "--display-name",
        default=None,
        help="Display name in Agent Runtime (defaults to agent_dir with hyphens).",
    )
    parser.add_argument(
        "--agent-engine-id",
        default=None,
        help="Existing Agent Engine ID to update in place or delete.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Runtime environment variable (repeatable).",
    )
    parser.add_argument(
        "--egress-gateway",
        default=None,
        help="Agent-to-Anywhere egress Agent Gateway name or full resource path.",
    )
    parser.add_argument(
        "--ingress-gateway",
        default=None,
        help="Optional Client-to-Agent ingress Agent Gateway name or full resource path.",
    )
    parser.add_argument(
        "--grant-invoker",
        default=None,
        metavar="PRINCIPAL",
        help="Grant resource-level roles/aiplatform.user on --agent-engine-id to PRINCIPAL.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the Agent Engine specified by --agent-engine-id (with force=True).",
    )
    return parser.parse_args()


def _merge_invoker_policy(policy: dict, principal: str, role: str = "roles/aiplatform.user") -> tuple[dict, bool]:
    bindings = list(policy.get("bindings", []))
    for binding in bindings:
        if binding.get("role") == role and not binding.get("condition"):
            members = list(binding.get("members", []))
            if principal in members:
                return policy, False
            members.append(principal)
            binding["members"] = members
            policy = {**policy, "bindings": bindings}
            return policy, True
    bindings.append({"role": role, "members": [principal]})
    return {**policy, "bindings": bindings}, True


def _grant_invoker(*, project: str, region: str, engine_id: str, principal: str) -> None:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    base_url = (
        f"https://{region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{project}/locations/{region}/reasoningEngines/{engine_id}"
    )
    get_resp = session.post(f"{base_url}:getIamPolicy", json={})
    get_resp.raise_for_status()
    policy = get_resp.json()

    updated_policy, changed = _merge_invoker_policy(policy, principal)
    if not changed:
        print(
            f"Principal '{principal}' already has roles/aiplatform.user on "
            f"reasoningEngines/{engine_id}."
        )
        return

    set_resp = session.post(
        f"{base_url}:setIamPolicy",
        json={"policy": updated_policy},
    )
    set_resp.raise_for_status()
    print(
        f"Granted roles/aiplatform.user on "
        f"projects/{project}/locations/{region}/reasoningEngines/{engine_id} "
        f"to {principal}."
    )


def _resolve_gateway_name(gateway: str, project: str, region: str) -> str:
    if gateway.startswith("projects/"):
        return gateway
    return f"projects/{project}/locations/{region}/agentGateways/{gateway}"


def _build_gateway_config(
    *,
    egress_gateway: str | None,
    ingress_gateway: str | None,
    project: str,
    region: str,
) -> dict | None:
    gateway_config: dict = {}
    if egress_gateway:
        gateway_config["agent_to_anywhere_config"] = {
            "agent_gateway": _resolve_gateway_name(egress_gateway, project, region)
        }
    if ingress_gateway:
        gateway_config["client_to_agent_config"] = {
            "agent_gateway": _resolve_gateway_name(ingress_gateway, project, region)
        }
    return gateway_config or None


def _bind_gateways(
    *,
    project: str,
    region: str,
    engine_id: str,
    egress_gateway: str | None,
    ingress_gateway: str | None,
) -> None:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    api_root = f"https://{region}-aiplatform.googleapis.com/v1beta1"
    resource_name = f"projects/{project}/locations/{region}/reasoningEngines/{engine_id}"

    gw_body: dict = {}
    if egress_gateway:
        gw_body["agentToAnywhereConfig"] = {
            "agentGateway": _resolve_gateway_name(egress_gateway, project, region)
        }
    if ingress_gateway:
        gw_body["clientToAgentConfig"] = {
            "agentGateway": _resolve_gateway_name(ingress_gateway, project, region)
        }

    print(f"Binding Agent Gateway(s) to {resource_name}...")
    resp = session.patch(
        f"{api_root}/{resource_name}",
        params={"updateMask": "spec.deployment_spec.agent_gateway_config"},
        json={"spec": {"deploymentSpec": {"agentGatewayConfig": gw_body}}},
    )
    resp.raise_for_status()
    op = resp.json()
    op_name = op["name"]

    while not op.get("done"):
        time.sleep(10)
        poll_resp = session.get(f"{api_root}/{op_name}")
        poll_resp.raise_for_status()
        op = poll_resp.json()

    if op.get("error"):
        raise RuntimeError(f"Failed to bind Agent Gateway(s): {op['error']}")

    bound = (
        op.get("response", {})
        .get("spec", {})
        .get("deploymentSpec", {})
        .get("agentGatewayConfig", gw_body)
    )
    print(f"Updated: {resource_name}")
    print(f"Agent Gateway Config: {bound}")


def main() -> None:
    args = parse_args()

    if args.grant_invoker:
        if not args.agent_engine_id:
            raise SystemExit("--grant-invoker requires --agent-engine-id.")
        _grant_invoker(
            project=args.project,
            region=args.region,
            engine_id=args.agent_engine_id,
            principal=args.grant_invoker,
        )
        return

    client = vertexai.Client(
        project=args.project,
        location=args.region,
        http_options={"api_version": "v1beta1"},
    )

    if args.delete:
        if not args.agent_engine_id:
            raise SystemExit("--delete requires --agent-engine-id.")
        resource_name = (
            f"projects/{args.project}/locations/{args.region}"
            f"/reasoningEngines/{args.agent_engine_id}"
        )
        print(f"Deleting Agent Runtime instance {resource_name} (force=True)...")
        op = client.agent_engines.delete(name=resource_name, force=True)
        done_op = _agent_engines_utils._await_operation(
            operation_name=op.name,
            get_operation_fn=client.agent_engines._get_agent_operation,
        )
        if getattr(done_op, "error", None):
            raise RuntimeError(f"Failed to delete Agent Engine: {done_op.error}")
        print(f"Deleted: {resource_name}")
        return

    gateway_config = _build_gateway_config(
        egress_gateway=args.egress_gateway,
        ingress_gateway=args.ingress_gateway,
        project=args.project,
        region=args.region,
    )

    # Gateway-only update when agent_dir is omitted
    if not args.agent_dir:
        if not args.agent_engine_id or not gateway_config:
            raise SystemExit(
                "Provide agent_dir to deploy, or --agent-engine-id with "
                "--egress-gateway/--ingress-gateway (or --grant-invoker / --delete)."
            )
        _bind_gateways(
            project=args.project,
            region=args.region,
            engine_id=args.agent_engine_id,
            egress_gateway=args.egress_gateway,
            ingress_gateway=args.ingress_gateway,
        )
        return

    display_name = args.display_name or args.agent_dir.replace("_", "-")
    base_dir = Path(__file__).resolve().parent

    entrypoint_objects = {
        "currency_agent": "currency_a2a_agent",
        "travel_agent": "travel_a2a_agent",
    }
    entrypoint_object = entrypoint_objects[args.agent_dir]
    runtime_path = base_dir / "a2a_runtime.py"
    spec = importlib.util.spec_from_file_location("_a2a_runtime_inspect", runtime_path)
    runtime_module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(runtime_module)
    a2a_agent = getattr(runtime_module, entrypoint_object)

    ops = a2a_agent.register_operations()
    class_methods_proto = _agent_engines._generate_class_methods_spec_or_raise(
        agent_engine=a2a_agent,
        operations=ops,
    )
    class_methods = [
        json_format.MessageToDict(cm, preserving_proto_field_name=True)
        for cm in class_methods_proto
    ]

    env_vars = {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "REGION": args.region,
    }
    for item in args.env:
        if "=" not in item:
            raise SystemExit(f"Invalid --env value (expected KEY=VALUE): {item}")
        k, v = item.split("=", 1)
        env_vars[k] = v

    config: dict = {
        "display_name": display_name,
        "entrypoint_module": "a2a_runtime",
        "entrypoint_object": entrypoint_object,
        "source_packages": ["a2a_runtime.py", args.agent_dir],
        "requirements_file": f"{args.agent_dir}/requirements.txt",
        "class_methods": class_methods,
        "agent_framework": "google-adk",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "env_vars": env_vars,
    }
    if gateway_config:
        config["agent_gateway_config"] = gateway_config

    if args.agent_engine_id:
        resource_name = (
            f"projects/{args.project}/locations/{args.region}"
            f"/reasoningEngines/{args.agent_engine_id}"
        )
        print(f"Updating A2A Agent Runtime instance {resource_name}...")
        engine = client.agent_engines.update(name=resource_name, config=config)
    else:
        print(f"Creating A2A Agent Runtime instance '{display_name}'...")
        engine = client.agent_engines.create(config=config)

    api_resource = engine.api_resource
    engine_id = api_resource.name.split("/")[-1]
    effective_identity = getattr(api_resource.spec, "effective_identity", None)
    card_url = (
        f"https://{args.region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{args.project}/locations/{args.region}/"
        f"reasoningEngines/{engine_id}/a2a/v1/card"
    )
    prefix = args.agent_dir.upper()
    print(f"Deployed: {api_resource.name}")
    print(f"Engine ID: {engine_id}")
    if effective_identity:
        print(f"Agent Identity: principal://{effective_identity}")
    print(f"A2A Agent Card URL: {card_url}")
    print()
    print("# Export for subsequent steps:")
    print(f'export {prefix}_ENGINE_ID="{engine_id}"')
    if effective_identity:
        print(f'export {prefix}_PRINCIPAL="principal://{effective_identity}"')
    print(f'export {prefix}_CARD_URL="{card_url}"')


if __name__ == "__main__":
    main()
