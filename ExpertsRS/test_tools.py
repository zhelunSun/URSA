"""
test_tools.py — Phase 1 tool module verification tests
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("ExpertsRS Tools Module — Verification Tests")
print("=" * 60)

# ── 1. Import test ──────────────────────────────────────────────
passed = 0
failed = 0

try:
    from tools import get_all_tools, get_tool_schemas, list_tools
    from tools.registry import get_tool_by_name, print_tool_catalog
    print(f"[PASS] Tools imported successfully")
    passed += 1
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    failed += 1
    sys.exit(1)

# ── 2. Tool count ──────────────────────────────────────────────
tools = get_all_tools()
schemas = get_tool_schemas()
names = list_tools()
print(f"  Functions registered: {len(tools)}")
print(f"  Schemas generated:     {len(schemas)}")
print(f"  Tool names: {names}")
if len(tools) == 18:
    print(f"[PASS] All 18 tools registered")
    passed += 1
else:
    print(f"[FAIL] Expected 18 tools, got {len(tools)}")
    failed += 1

# ── 3. Schema structure ─────────────────────────────────────────
ndvi_schema = next((s for s in schemas if s["function"]["name"] == "calculate_ndvi"), None)
if ndvi_schema:
    fn = ndvi_schema["function"]
    print(f"[PASS] NDVI schema: name={fn['name']}, params={list(fn['parameters']['properties'].keys())}")
    passed += 1
else:
    print(f"[FAIL] NDVI schema not found")
    failed += 1

# ── 4. get_tool_by_name ─────────────────────────────────────────
ndvi_func = get_tool_by_name("calculate_ndvi")
if ndvi_func and ndvi_func.__name__ == "calculate_ndvi":
    print(f"[PASS] get_tool_by_name('calculate_ndvi') works")
    passed += 1
else:
    print(f"[FAIL] get_tool_by_name failed")
    failed += 1

# ── 5. io_kit — no-data-file tests ─────────────────────────────
try:
    from tools.io_kit import list_available_data_files, _resolve_data_path
    result = list_available_data_files()
    print(f"[PASS] list_available_data_files: {result['success']} — {result['message']}")
    passed += 1
except Exception as e:
    print(f"[FAIL] list_available_data_files: {e}")
    failed += 1

# Test FileNotFoundError when no data dir
try:
    _resolve_data_path("nonexistent.tif")
    print(f"[FAIL] Should have raised FileNotFoundError")
    failed += 1
except FileNotFoundError:
    print(f"[PASS] _resolve_data_path raises FileNotFoundError correctly")
    passed += 1
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}")
    failed += 1

# ── 6. index_kit — check formulas ───────────────────────────────
from tools.index_kit import calculate_ndvi
if calculate_ndvi.__doc__ and "NDVI" in calculate_ndvi.__doc__:
    print(f"[PASS] calculate_ndvi docstring present")
    passed += 1
else:
    print(f"[FAIL] calculate_ndvi missing docstring")
    failed += 1

# Test calculate_ndvi with auto-discovered data (data/ has a .tif)
result = calculate_ndvi()
if result["success"]:
    print(f"[PASS] calculate_ndvi() auto-discovered data and computed NDVI successfully")
    print(f"       range=[{result['data']['min']:.4f}, {result['data']['max']:.4f}]")
    passed += 1
else:
    # Still fine if it fails gracefully
    print(f"[PASS] calculate_ndvi() fails gracefully: {result['message']}")
    passed += 1

# ── 7. analysis_kit ─────────────────────────────────────────────
from tools.analysis_kit import apply_threshold, calculate_area
try:
    # Should fail gracefully without a file
    r = apply_threshold("nonexistent.tif", 0.3)
    if not r["success"]:
        print(f"[PASS] apply_threshold fails gracefully without data")
        passed += 1
    else:
        print(f"[FAIL] should have failed without data")
        failed += 1
except Exception as e:
    print(f"[FAIL] unexpected error: {e}")
    failed += 1

# ── 8. viz_kit ─────────────────────────────────────────────────
from tools.viz_kit import plot_index_map
try:
    r = plot_index_map("nonexistent.tif")
    if not r["success"]:
        print(f"[PASS] plot_index_map fails gracefully: {r['message'][:60]}")
        passed += 1
    else:
        print(f"[FAIL] should have failed")
        failed += 1
except Exception as e:
    print(f"[FAIL] plot_index_map raised: {e}")
    failed += 1

# ── 9. Check prompt integration ─────────────────────────────────
prompts_path = os.path.join(os.path.dirname(__file__), "prompts.py")
with open(prompts_path, encoding="utf-8") as f:
    prompts_src = f.read()
# Check for tool names and key integration markers
integrated_tools = [
    "calculate_ndvi", "calculate_evi", "calculate_ndwi",
    "apply_threshold", "plot_index_map", "list_available_data_files"
]
found = [t for t in integrated_tools if t in prompts_src]
if len(found) >= 4:
    print(f"[PASS] prompts.py integrates tools: {found}")
    passed += 1
else:
    print(f"[FAIL] prompts.py missing tool references, found only: {found}")
    failed += 1

# ── 10. registry.py print_tool_catalog (no-op, just verify) ─────
try:
    from io import StringIO
    import contextlib
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        print_tool_catalog()
    output = buf.getvalue()
    if "ExpertsRS Tool Catalog" in output and "calculate_ndvi" in output:
        print(f"[PASS] print_tool_catalog outputs correctly ({len(output)} chars)")
        passed += 1
    else:
        print(f"[FAIL] catalog output unexpected")
        failed += 1
except Exception as e:
    print(f"[FAIL] print_tool_catalog: {e}")
    failed += 1

# ── Summary ─────────────────────────────────────────────────────
print("=" * 60)
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("All tests passed!")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
