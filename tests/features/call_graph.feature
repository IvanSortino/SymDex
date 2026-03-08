# tests/features/call_graph.feature
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

Feature: Call Graph

  Background:
    Given a Python file where "caller_func" calls "callee_func" has been indexed

  Scenario: Get callers of a function
    When I call get_callers with name "callee_func" and repo "cg_test"
    Then the response contains a "callers" list
    And the callers list includes a symbol named "caller_func"

  Scenario: Get callees of a function
    When I call get_callees with name "caller_func" and repo "cg_test"
    Then the response contains a "callees" list
    And the callees list includes an entry with name "callee_func"

  Scenario: Unresolved external call has null file
    Given a Python file that calls an external library function has been indexed
    When I call get_callees with name "external_caller" and repo "cg_external"
    Then the callees list contains an entry where callee_file is null

  Scenario: Re-indexing does not duplicate edges
    Given the call graph repo has been indexed once
    When I index the same folder again without changes
    And I call get_callees with name "caller_func" and repo "cg_dedup"
    Then the callees list contains "callee_func" exactly once
