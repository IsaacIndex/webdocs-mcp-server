import json
import os
import pyperclip


def update_mcp_path():
    # Get current directory
    current_dir = os.getcwd()

    # Read the mcp.json file
    with open('mcp.json', 'r') as f:
        mcp_data = json.load(f)

    # Update the system directory in the args array
    mcp_data['mcpServers']['web-content']['args'][2] = current_dir

    # Convert the updated dictionary to a formatted JSON string
    updated_json = json.dumps(mcp_data, indent=2)

    # Copy the updated JSON to clipboard
    pyperclip.copy(updated_json)

    print(f"Updated directory in memory: {current_dir}")
    print("Updated mcp.json content has been copied to clipboard!")


if __name__ == "__main__":
    update_mcp_path()
