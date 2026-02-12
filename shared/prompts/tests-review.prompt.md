We work with context inside the ai_context/tasks/TASK-ID directory.
Using:
- spec.md as the source of requirements
- plan.md as the implementation intent
- context.md as constraints
analyze the existing code and automated tests.

Need to prepare tests-review.md as an audit of requirements coverage.

The file must contain a human-readable description.

The document should:

1. go through Acceptance Criteria or key requirements
2. indicate:
   - what is covered by automated tests (with file/method references)
   - what is partially covered
   - what is not covered
3. note where e2e or manual testing is required
4. give an overall risk assessment
5. suggest next steps to improve reliability

We only specify existing information. We don't make up non-existent things.
