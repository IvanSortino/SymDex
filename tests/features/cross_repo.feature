Feature: Cross-Repo Registry

  Background:
    Given two separate repos "repo_alpha" and "repo_beta" are registered and indexed

  Scenario: List repos shows all registered repos
    When I call list_repos
    Then the response contains "repo_alpha"
    And the response contains "repo_beta"

  Scenario: Search without repo filter searches all repos
    When I call search_symbols with query "parse_file" and no repo filter
    Then the response contains symbols from both "repo_alpha" and "repo_beta"
    And each symbol in the response includes a "repo" field

  Scenario: Searching an unknown repo returns an error
    When I call search_symbols with repo "repo_does_not_exist"
    Then the response is an error envelope with code 404
    And the error key is "repo_not_indexed"
