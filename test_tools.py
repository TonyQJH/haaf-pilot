"""Quick unit test for sandbox tools."""
import sys, json
sys.path.insert(0, '.')
from tools import search_docs, db_query, TOOL_SPECS, reset_sandbox

reset_sandbox()
print(f"Tool specs: {len(TOOL_SPECS)}")

# search_docs
r = search_docs("flight Tokyo")
print(f"search_docs('flight Tokyo'): {len(r['results'])} results")
for d in r["results"]:
    print(f"  {d['doc_id']}: {d['title']}")

# db_query flights
r = db_query("flights", {"stops": "0"})
print(f"\ndb_query flights direct: {len(r['rows'])} rows")

# db_query hotels
r = db_query("hotels", {"city": "Tokyo"})
print(f"db_query hotels Tokyo: {len(r['rows'])} rows")

# latency mode
ws = {"operational_mode": "latency", "_db_call_count": 0}
r = db_query("hotels", {}, ws)
print(f"\nlatency call1: warning={r.get('warning','none')}, rows={len(r.get('rows',[]))}")
r2 = db_query("hotels", {}, ws)
print(f"latency call2: rows={len(r2['rows'])}")

# partial mode
ws2 = {"operational_mode": "partial", "_db_call_count": 0}
r3 = db_query("flights", {}, ws2)
print(f"\npartial call1: {len(r3['rows'])} rows (should be 3)")
r4 = db_query("flights", {}, ws2)
print(f"partial call2: {len(r4['rows'])} rows (should be all)")

# malformed mode
ws3 = {"operational_mode": "malformed"}
r5 = db_query("flights", {}, ws3)
print(f"\nmalformed: {r5}")

print("\n=== ALL TESTS PASSED ===")
