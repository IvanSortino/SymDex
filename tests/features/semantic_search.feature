Feature: Semantic Search

  Background:
    Given a folder with Python files containing docstrings has been indexed

  Scenario: Semantic search returns relevant results
    When I call semantic_search with query "parse source code"
    Then the response contains a "symbols" list
    And at least one symbol name or docstring relates to parsing

  Scenario: Each result has a similarity score
    When I call semantic_search with query "database storage"
    Then each symbol in the response has a "score" field between 0 and 1

  Scenario: Semantic search respects repo filter
    Given two repos are indexed
    When I call semantic_search with query "parse file" filtered to one repo
    Then all returned symbols belong to that repo

  Scenario: Symbol with null embedding does not crash search
    Given a symbol exists with a NULL embedding value
    When I call semantic_search with any query
    Then the response is successful
    And the null-embedding symbol is not included in the results

  Scenario: Semantic search via CLI
    When I run "symdex semantic" with query "parse source code"
    Then the CLI command exits with code 0
    And the CLI output contains at least one symbol row
