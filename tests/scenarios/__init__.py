"""Scenario tests.

One test module per scenario in guardian_scenarios.md. Each test injects
the scenario's triggering events into the bus and asserts on the
agent's tool-call sequence + final Event Log shape.

Naming convention: test_scenario_<NN>_<short_name>.py
"""
