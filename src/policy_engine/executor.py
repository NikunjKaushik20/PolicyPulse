from typing import Dict, Any, List, Union

class PolicyCodeExecutor:
    """
    Executes JSON Logic rules against a user context.
    Custom implementation to ensure stability without external dependencies.
    """
    
    def evaluate(self, logic: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluate a logic rule against context.
        """
        if not logic:
            return True
            
        try:
            return self._eval(logic, context)
        except Exception as e:
            print(f"Logic evaluation error: {e}")
            return False

    def _eval(self, logic: Any, context: Dict[str, Any]) -> Any:
        # Primitive types
        if not isinstance(logic, dict):
            return logic
            
        # Operator usually is the only key
        op = list(logic.keys())[0]
        args = logic[op]
        
        # Ensure args is a list for most operators
        if not isinstance(args, list) and op != "var":
            args = [args]
                
        if op == "var":
            # Extract variable from context
            path = args if isinstance(args, str) else args[0]
            # Handle user.age vs just age
            parts = path.split(".")
            val = context
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    return None
            return val
            
        # Recursive evaluation of arguments
        eval_args = [self._eval(a, context) for a in args]
        
        if op == "==": return eval_args[0] == eval_args[1]
        if op == "===": return eval_args[0] == eval_args[1]
        if op == "!=": return eval_args[0] != eval_args[1]
        if op == "!==": return eval_args[0] != eval_args[1]
        if op == ">": return float(eval_args[0]) > float(eval_args[1]) # ensure float comparison
        if op == ">=": return float(eval_args[0]) >= float(eval_args[1])
        if op == "<": return float(eval_args[0]) < float(eval_args[1])
        if op == "<=": return float(eval_args[0]) <= float(eval_args[1])
        
        if op == "and": return all(eval_args)
        if op == "or": return any(eval_args)
        if op == "!": return not eval_args[0]
        
        return False

    def explain_failure(self, logic: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """
        Walk the logic tree to find WHICH condition failed.
        """
        failures = []
        if "and" in logic:
            for condition in logic["and"]:
                if not self.evaluate(condition, context):
                    failures.append(self._humanize_condition(condition, context))
        elif not self.evaluate(logic, context):
            failures.append(self._humanize_condition(logic, context))
            
        return failures

    def _humanize_condition(self, condition: Dict, context: Dict) -> str:
        """
        Convert a raw JSON Logic condition into a human-readable failure reason.
        """
        try:
            op = list(condition.keys())[0]
            args = condition[op]
            
            if op == "var":
                return f"Missing required attribute: {args}"
                
            if isinstance(args, list) and len(args) == 2:
                # Try to get the actual value for the variable part
                val_lookup = args[0]
                target_val = args[1]
                
                actual_val = "unknown"
                if isinstance(val_lookup, dict) and "var" in val_lookup:
                    var_name = val_lookup["var"]
                    if isinstance(var_name, list): var_name = var_name[0]
                    # Evaluate just the var part
                    actual_val = self._eval(val_lookup, context)
                
                if op == ">": return f"Value {actual_val} is not greater than {target_val}"
                if op == ">=": return f"Value {actual_val} is not greater than or equal to {target_val}"
                if op == "<": return f"Value {actual_val} is not less than {target_val}"
                if op == "<=": return f"Value {actual_val} is not less than or equal to {target_val}"
                if op == "==": return f"Value {actual_val} does not match required {target_val}"

            return f"Condition failed: {condition}"
        except:
            return f"Complex condition failed: {condition}"
