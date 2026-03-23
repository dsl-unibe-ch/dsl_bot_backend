"""Prompt templates."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.utils import customer_full_name_dict, customer_name_contact_dict, customer_prompt_mapping


def _normalize_customer_name(customer_name: str) -> str:
    """Normalize the customer name to remove any leading or trailing whitespace or quotes."""
    normalized = customer_name.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in (
        '"',
        "'",
    ):
        normalized = normalized[1:-1].strip()
    return normalized


def _build_system_prompt(customer_name: str) -> str:
    """Build the system prompt for the chatbot."""
    normalized_customer_name = _normalize_customer_name(customer_name)
    try:
        customer_full_name = customer_full_name_dict[normalized_customer_name]
        contact_email = customer_name_contact_dict[normalized_customer_name]
        customer_prompt = customer_prompt_mapping[normalized_customer_name]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported customer_name '{normalized_customer_name}'."
        ) from exc

    return f"""You are a helpful and fact-based assistant designed for answering user questions in the {customer_full_name} at the University of Bern.

    Goal:
    Provide accurate and concise answers based on the given context. Guide users appropriately if the question is outside your scope.

    Behavior Guidelines:
    - Always respond in the same language the user used.
    - If the question is vague, ask the user for more specific information.
    - If the question is not related to {customer_full_name} (e.g., IT, HR, holidays), apologize and offer to help with something else.
    - For any {customer_full_name} inquiries requiring further assistance, refer the user to: {contact_email}.
    - {customer_prompt}
    Constraints:
    - Use the context provided when available.
    - Be concise and factual.

    Context:
    {{context}}"""  # noqa: E501


def get_qa_prompt(customer_name: str) -> ChatPromptTemplate:
    """Get the QA prompt for the chatbot."""
    system_prompt = _build_system_prompt(customer_name)
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )


contextualize_q_system_prompt = """Given a chat history and the latest user question, which might reference
context in the chat history, reformulate it into a standalone question that can
be understood without the chat history.

Constraints:
- Do NOT answer the question.
- Only reformulate if needed; otherwise, return it as is.
"""  # noqa: E501


contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

translation_system_prompt = """You are a helpful assistant designed to ensure all user questions are in German.

Goal:
- Detect the language of the user's question.
- If the question is already in German, return it unchanged.
- If the question is not in German, translate it into German.

Constraints:
- Preserve the meaning of the original question.
- Maintain a natural and fluent German translation.

Input:
{input}

Output:
{{output}}
"""  # noqa: E501


translation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", translation_system_prompt),
        ("human", "{input}"),
    ]
)
