import tempfile, os
from testforge.llm import MockLLM
from testforge.tool_dispatcher import ToolDispatcher
from testforge.agent_loop import AgentLoop

script = [
    '{"tool": "write_file", "params": {"path": "test_dummy.py", "content": "def test_ok():\\n    assert 1 == 1\\n"}}',
    '{"tool": "run_tests", "params": {"test_path": "test_dummy.py"}}',
]

with tempfile.TemporaryDirectory() as tmpdir:
    print("TMPDIR:", tmpdir)
    llm = MockLLM(script=script)
    dispatcher = ToolDispatcher(workspace_dir=tmpdir)
    loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=3)
    result = loop.run(initial_context='Generate tests')
    
    # Check if the file exists
    test_file = os.path.join(tmpdir, "test_dummy.py")
    print("\nFile exists:", os.path.exists(test_file))
    if os.path.exists(test_file):
        with open(test_file, "r") as f:
            print("File content:")
            print(f.read())
    print()
    
    for record in result['history']:
        if record.test_result:
            print('RAW OUTPUT:')
            print(record.test_result.raw_output[:2000])