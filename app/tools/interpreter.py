import sys
import io
import traceback
import logging
from langchain_core.tools import tool

logger = logging.getLogger("research_engine.tools.interpreter")

@tool
def execute_python_code(code: str) -> str:
    """
    Execute Python code in an isolated sandbox environment. 
    Use this for math computations, financial forecasting models, and data calculations.
    Standard output is captured and returned.
    """
    logger.info("Executing Python code interpreter...")
    
    # Redirect standard output
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    # Create execution scope
    local_vars = {}
    global_vars = {"__builtins__": __builtins__}
    
    try:
        # Preprocess code string to strip any markdown fences if the agent adds them
        clean_code = code
        if clean_code.startswith("```python"):
            clean_code = clean_code[9:]
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3]
            
        exec(clean_code, global_vars, local_vars)
        sys.stdout = old_stdout
        return redirected_output.getvalue() or "Code executed successfully with no stdout output."
    except Exception as e:
        sys.stdout = old_stdout
        error_msg = traceback.format_exc()
        logger.error(f"Python interpreter error: {e}")
        return f"Execution Error:\n{error_msg}"
