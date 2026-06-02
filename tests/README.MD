# Test Strategy

The goal of this document is to define the test strategy of the chatbot

## Data Sources And What To Measure From Them:

There are three main sources of data

1. **Human evaluator annotations**
  These are high quality annotations by the customer SMEs where each case may contain a query, a set of relevant documents with each document containing evidence spans and URL, expected answer. This data is useful for testing
    1. Retrieval quality:
      - Did the search retrieve the expected document?
      - Did the expected document appear in top-k?
      - Did the retrieved chunks contain the evidence span?
    2. Answer quality
    - Did the bot answer the question correctly?
      - Is the answer consistent with the expected answer?
      - Is the answer grounded in the retrieved evidence?
2. **AI generated annotations from real user interactions and feedback**
  This is available after having launched the bot. This is useful for studying chatbot behavioural regression, basically what type of cases are to be covered and how the bot behaves in the production. This data can be useful to check for in-scope and out-of-scope classification, language consistency, whether the question is answerable or the bot should route the user somewhere else, whether retrieval should be done or not.
3. **AI-generated annotations from the knowledge base**
  Given an Excel export of the knowledge base, AI can generate two additional types of questions:
  1. Answerable questions with answers: Questions whose answers are present in the documents.
    1. For each question, further generate, the set of relevant documents with each document containing evidence spans and URL, expected answer
  2. In-scope but unanswerable questions : Questions that belong to the domain, but whose answer is not present in the documents. Note that this different from out-of-scope. The question belongs to the domain, but the answer is not available in the current knowledge base.
4. **Knowledge Base**

## Test Categories

### 1. Behavioural Regression tests

#### Data Source:

1. AI generated annotations from real user interactions and feedback
2. Knowledge base

#### Dataset Schema

```bash
    { 
      "id":"{CUSTOMER}_001,
      "input":{
              "query:"Was ist das Innovation Office?",
              "history": []
              },
      "expected": {
              "scope_label": "in_scope" # "out_of_scope"
              "answerability": answerable_from_docs  # unanswerable_from_docs
              "expected_action": "answer" # clarify, defer_or_decline
              "same_language": true # false
      }
    }
```

#### Purpose

This tests answer questions such as 

- Is the user query in scope?
- Should the bot answer directly or ask a clarification question or decline/defer to a human contact?
- Should it avoid retrieval?
- Does it reply in the same language?
- Is the query answerable from docs? 
  - If yes, does it answer?
  - If not (implying that the user query is in scope but the documents do not contain this information? For eg: "When will the deadlines be for next year?"), does the bot decline and defer? This is important because “in scope” does not always mean “answerable.”

This can help to catch cases where the bot

- answers HR questions with the Unit's fallback email
- retrieves documents for “Hi” or “test”
- answers in German when the user asked for English
- invents facts or hallucinates or shows confidence for queries where it should not have answered.

#### Labels and Metrics


| What is being measured                          | Metrics                                                                                           | Labels                                             | Purpose                                                                                  |     |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------- | --- |
| Scope                                           | Acc, F1, Prec, Rec                                                                                | in_scope, out_of_scope                             | Is the user query in scope?                                                              |     |
| Expected Action                                 | Acc, F1, Prec, Rec                                                                                | answer, clarify, defer_or_decline                  | Should the bot answer directly or ask a clarifying question or decline/defer to a human? |     |
| Answerability                                   | Acc, F1, Prec, Rec                                                                                | answerable_from_docs, unanswerable_from_docs False | Is this query answerable given the knowledge base?                                       |     |
| Language Handling                               | Acc                                                                                               | True, False                                        | Does the bot answer in the user's own language                                           |     |
| Retrieval Appropriateness                       | (Count of cases where actual_retrieved == expected_should_retrieve / Total cases)                 | Not Applicable                                     | Should the bot retrieve or not?                                                          |     |
| Knowledge Gap Handling/ Unsupported Answer Rate | (Count of in-scope cases where the bot answers directly/ Count of unanswerable_from_docs queries) | Not Applicable                                     | How does the bot behave when user query is in scope but unanswerable, lower the better   |     |


### 2. Retrieval evaluation tests

#### Data Source:

1. Human evaluator annotations
2. AI-generated annotations from the knowledge base

#### Dataset Schema

```bash
  {
    "id": "{CUSTOMER}_retrieval_001",
    "query": "Was ist der Unterschied zwischen Zwischen- und Schlussevaluation?",
    "expected": {
      "relevant_documents": [
        {
          "document_id": "doc_123",
          "url": "https://...",
          "evidence_spans": [
            "..."
          ]
        }
      ]
    }
  }

```

#### Purpose

This test measures the search quality and can ideally be run directly on the search pipeline which is useful for ETL quality consistency checks. However for simplicity of test design, the API endpoint for the bot may also be called directly to retrieve only the sources. The metrics are mostly precision@k, recall@k, whether the expected URL was fetched etc.

#### Labels and Metrics


| What is being measured | Metrics                                                                                               | Purpose                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Hit Rate               | Number of Queries with at least one relevant document retrieved/Total Number of Queries               | Shows how often retrieved docs exactly match the expected ones, higher is better. |
| Recall@k               | (Number of relevant docs in top K) / (Total number of relevant docs)                                  | Measures how many relevant items were found out of all possible relevant items    |
| Precision@K            | (Number of relevant docs in top K) / K                                                                | Measures the proportion of relevant items within the top K retrieved results      |
| Evidence Hit Rate@K    | (Queries where at least one top-k retrieved chunk contains an expected evidence span / total queries) | Measures if any expected evidence span appears in any of the top-k chunks         |


### 3. Answer Correctness

#### Data Source:

Human Evaluator Annotations
AI-generated annotations from the knowledge base

#### Dataset Schema:

```bash
    {
      "id": "{CUSTOMER}_001",
      "input": {
        "message": "Was ist der Unterschied zwischen Zwischen- und Schlussevaluation?",
        "history": []
      },
      "expected": {
        "answerability": "answerable_from_docs", # unanswerable_from_docs
        "expected_answer": "...",
        "expected_docs": {
          "relevant_documents": [
            {
              "document_id": "doc_123",
              "url": "https://...",
              "evidence_spans": [
                "..."
              ]
            }
          ]
      }
    }
```

#### Purpose

Checks whether the final bot answer matches the expected answer and is grounded in evidence. The metrics can be

- semantic similarity to ground-truth answer
- LLM-as-judge answer correctness

#### Labels and Metrics


| What is being measured | Metrics                                             | Labels                    | Purpose                                                                           |
| ---------------------- | --------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------- |
| Correctness Accuracy   | Count of Correct answers/Total Number of Queries    | 0 - Correct 1- Incorrect  | Shows how often retrieved docs exactly match the expected ones, higher is better. |
| Error Rate             | Count of Incorrect answers/ Total Number of Queries | 0 - Correct 1 - Incorrect | Measures how many relevant items were found out of all possible relevant items    |


