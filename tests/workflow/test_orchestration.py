"""Tests for Workflow DAG graph construction, validation, and node scheduling."""
import pytest
from shared.schemas.workflow import (
    WorkflowNode,
    WorkflowGraph,
    WorkflowCreate,
    WorkflowStatus,
    NodeStatus,
)


def test_workflow_graph_dag_dependencies():
    # Node 1: Ingest
    node1 = WorkflowNode(
        node_id="node-ingest",
        capability="rss_ingest",
        depends_on=[],
    )

    # Node 2: Cluster (depends on Node 1)
    node2 = WorkflowNode(
        node_id="node-cluster",
        capability="story_clustering",
        depends_on=["node-ingest"],
    )

    # Node 3: Fact verification (depends on Node 2)
    node3 = WorkflowNode(
        node_id="node-verify",
        capability="claim_verification",
        depends_on=["node-cluster"],
    )

    # Node 4: Synthesis report (depends on Node 3)
    node4 = WorkflowNode(
        node_id="node-report",
        capability="report_synthesis",
        depends_on=["node-verify"],
    )

    graph = WorkflowGraph(
        nodes=[node1, node2, node3, node4],
        edges=[
            ("node-ingest", "node-cluster"),
            ("node-cluster", "node-verify"),
            ("node-verify", "node-report"),
        ],
    )

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 3

    # Check root nodes (nodes with 0 dependencies)
    root_nodes = [n for n in graph.nodes if not n.depends_on]
    assert len(root_nodes) == 1
    assert root_nodes[0].node_id == "node-ingest"


def test_workflow_create_schema():
    wf_create = WorkflowCreate(
        name="Real-time AI News Pipeline",
        description="Ingests, verifies, and publishes AI news with source citations",
    )
    assert wf_create.name == "Real-time AI News Pipeline"
