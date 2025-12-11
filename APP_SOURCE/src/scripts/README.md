# Scripts Directory

This directory contains business logic scripts that can be configured and executed through the Data Forge Studio interface.

## Built-in Scripts

- **file_dispatcher.py**: Dispatches files from root folder to contract/dataset folders based on filename patterns
- **data_loader.py**: Loads data files into databases

## Adding Custom Scripts

Users can add their own custom scripts to this directory. Your custom scripts will be available alongside the built-in scripts.

### How to Add a Custom Script

1. Create a new Python file in this directory (e.g., `my_custom_script.py`)
2. Implement your script logic as a class or functions
3. Register your script in the database through the UI (Scripts Manager)
4. Configure parameters and create jobs to execute your script

### Example Custom Script Structure

```python
"""
My Custom Script - Description of what it does
"""
from pathlib import Path
from typing import Dict, Any
from ..utils.logger import logger


class MyCustomProcessor:
    """Description of your processor"""

    def __init__(self, param1: str, param2: int):
        self.param1 = param1
        self.param2 = param2
        self.stats = {
            "processed": 0,
            "errors": 0
        }

    def process(self) -> Dict[str, Any]:
        """
        Main processing method

        Returns:
            Dictionary with statistics about the operation
        """
        try:
            # Your processing logic here
            logger.info(f"Processing with param1={self.param1}, param2={self.param2}")

            # Example processing
            self.stats["processed"] += 1

            return self.stats

        except Exception as e:
            logger.error(f"Error in processing: {e}")
            self.stats["errors"] += 1
            return self.stats
```

### Integration with Jobs Manager

To make your script available in the Jobs Manager:

1. Go to **Scripts Manager** in the UI
2. Click **"New Script"**
3. Configure:
   - **Name**: Display name for your script
   - **Type**: Select "custom"
   - **Description**: What your script does
   - **Parameters Schema**: JSON defining required parameters
     ```json
     {
       "param1": "string",
       "param2": "integer"
     }
     ```

4. Create a **Job** that uses your script with specific parameter values

### Best Practices

- Keep scripts focused on a single responsibility
- Use the logger for tracking progress and errors
- Return statistics/results as dictionaries
- Handle errors gracefully
- Document your parameters and return values
- Use type hints for better code clarity

### Script Types

Scripts can be categorized as:

- **dispatch_files**: File organization/routing scripts
- **load_to_database**: Data loading/ETL scripts
- **custom**: Any other custom processing logic

Choose the appropriate type when registering your script in the database.
