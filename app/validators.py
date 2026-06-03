from typing import Any, Optional, Dict, List

class ToolValidator:
    # Maps intent to allowed tools
    INTENT_TO_TOOLS = {
        "show_cart": ["show_cart"],
        "add_to_cart": ["add_to_cart"],
        "remove_from_cart": ["remove_from_cart"],
        "clear_cart": ["clear_cart"],
        "checkout": ["checkout"],
        "get_order_status": ["get_order_status"],
    }

    @staticmethod
    def validate(intent: str, tool_name: str) -> str:
        allowed_tools = ToolValidator.INTENT_TO_TOOLS.get(intent)
        if allowed_tools and tool_name not in allowed_tools:
            return allowed_tools[0]  # Correct automatically to the intended tool
        return tool_name

class RequiredFieldsValidator:
    # Fields that MUST be present, excluding session_id
    REQUIRED_FIELDS = {
        "add_to_cart": ["product_name", "quantity", "price"],
        "remove_from_cart": ["product_name"],
        "get_order_status": ["order_id"],
    }

    @staticmethod
    def validate(tool_name: str, args: Dict[str, Any]) -> Optional[List[str]]:
        required = RequiredFieldsValidator.REQUIRED_FIELDS.get(tool_name, [])
        missing = [field for field in required if field not in args]
        return missing if missing else None
