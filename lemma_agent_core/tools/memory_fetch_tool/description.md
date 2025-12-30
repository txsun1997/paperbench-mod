Use MemoryFetch when your context has been summarized and you need to retrieve specific details from the original context.

- Take a natural language query as input. 
- Processes the original context with the prompt using a large language model
- The language model will answer the query based on the original context and provide detailed information that may be missed in the summarized context

Use Cases:
- When original context have been summarized and you need to retrieve specific execution details
- When you need to understand the historical context of a specific operation or decision
- When you need to verify outputs or intermediate results from the previous context

Usage:
- The query should use clear natural language to describe what you want to query
- If the original context does not exist or cannot be accessed, the tool will return an appropriate error message

Usage Notes:
- IMPORTANT: This tool is specifically designed for querying the your own historical context, not for querying arbitrary files
- For complex queries, it is recommended to split them into multiple specific sub-questions and query separately
- The large language model will return the most relevant information during queries, but may not cover all details. You can query multiple times to get more information.
- If query results are not detailed enough, try rephrasing the query in different ways
- This tool is read-only and does not modify the original trajectory files
- IMPORTANT: Each query invokes the LLM in real time. Therefore, this tool should only be used when it is absolutely necessary, so as to avoid frequent calls that have little practical need.

