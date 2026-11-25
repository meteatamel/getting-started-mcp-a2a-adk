"""Deploy an ADK agent as a native A2A agent on Vertex AI Agent Runtime.

Usage:
    uv run python deploy_a2a.py currency_agent \\
      --project=$PROJECT_ID \\
      --region=$REGION \\
      --display-name=currency-agent \\
      --env MCP_SERVER_NAME=$MCP_SERVER_NAME
"""

import argparse
import importlib.util
from pathlib import Path

from google.protobuf import json_format
import vertexai
from vertexai import types
from vertexai.agent_engines import _agent_engines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy an ADK agent as an A2A agent on Agent Runtime."
    )
    parser.add_argument(
        "agent_dir",
        choices=["currency_agent", "travel_agent"],
        help="Agent package directory to deploy.",
    )
    parser.add_argument("--project", required=True, help="Google Cloud project ID.")
    parser.add_argument("--region", required=True, help="Google Cloud region.")
    parser.add_argument("--display-name", required=True, help="Display name in Agent Runtime.")
    parser.add_argument(
        "--agent-engine-id",
        default=None,
        help="Optional existing Agent Engine ID to update in place.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Runtime environment variable (repeatable).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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

    config = {
        "display_name": args.display_name,
        "entrypoint_module": "a2a_runtime",
        "entrypoint_object": entrypoint_object,
        "source_packages": ["a2a_runtime.py", args.agent_dir],
        "requirements_file": f"{args.agent_dir}/requirements.txt",
        "class_methods": class_methods,
        "agent_framework": "google-adk",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "env_vars": env_vars,
    }

    client = vertexai.Client(
        project=args.project,
        location=args.region,
        http_options={"api_version": "v1beta1"},
    )

    if args.agent_engine_id:
        resource_name = (
            f"projects/{args.project}/locations/{args.region}"
            f"/reasoningEngines/{args.agent_engine_id}"
        )
        print(f"Updating A2A Agent Runtime instance {resource_name}...")
        engine = client.agent_engines.update(name=resource_name, config=config)
    else:
        print(f"Creating A2A Agent Runtime instance '{args.display_name}'...")
        engine = client.agent_engines.create(config=config)

    api_resource = engine.api_resource
    engine_id = api_resource.name.split("/")[-1]
    effective_identity = getattr(api_resource.spec, "effective_identity", None)
    card_url = (
        f"https://{args.region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{args.project}/locations/{args.region}/"
        f"reasoningEngines/{engine_id}/a2a/v1/card"
    )
    print(f"Deployed: {api_resource.name}")
    print(f"Engine ID: {engine_id}")
    if effective_identity:
        print(f"Agent Identity: principal://{effective_identity}")
    print(f"A2A Agent Card URL: {card_url}")


if __name__ == "__main__":
    main()
