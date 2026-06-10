"""
Compile every locale/<lang>/LC_MESSAGES/*.po into a binary .mo file.

Pure Python — needed on machines without GNU gettext (`msgfmt`), e.g. Windows
without the gettext tools installed. Run after editing any .po:

    python scripts/compile_translations.py

(Equivalent to Django's `manage.py compilemessages`, which requires gettext.)
"""
import struct
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCALE = BASE / "locale"


def _unescape(s: str) -> str:
    out, i = [], 0
    table = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(table.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _quoted(line: str) -> str:
    return line[line.index('"') + 1: line.rindex('"')]


def parse_po(text: str) -> dict:
    """Return {key: value}; plural keys are 'id\\x00plural', values 'one\\x00other'."""
    entries, cur, field = {}, {}, None

    def flush():
        nonlocal cur
        if "msgid" in cur:
            if "plural" in cur:
                key = cur["msgid"] + "\x00" + cur["plural"]
                val = cur.get("msgstr0", "") + "\x00" + cur.get("msgstr1", "")
                has = bool(cur.get("msgstr0") or cur.get("msgstr1"))
            else:
                key, val = cur["msgid"], cur.get("msgstr", "")
                has = bool(val)
            if has or cur["msgid"] == "":   # keep header (empty msgid)
                entries[key] = val
        cur = {}

    for raw in text.split("\n"):
        st = raw.strip()
        if st == "":
            flush(); field = None; continue
        if st.startswith("#"):
            continue
        if st.startswith("msgid_plural"):
            cur["plural"] = _unescape(_quoted(st)); field = "plural"
        elif st.startswith("msgid"):
            flush(); cur = {"msgid": _unescape(_quoted(st))}; field = "msgid"
        elif st.startswith("msgstr["):
            idx = st[st.index("[") + 1: st.index("]")]
            cur["msgstr" + idx] = _unescape(_quoted(st)); field = "msgstr" + idx
        elif st.startswith("msgstr"):
            cur["msgstr"] = _unescape(_quoted(st)); field = "msgstr"
        elif st.startswith('"') and field:
            cur[field] = cur.get(field, "") + _unescape(_quoted(st))
    flush()
    return entries


def make_mo(entries: dict) -> bytes:
    items = sorted((k.encode("utf-8"), v.encode("utf-8")) for k, v in entries.items())
    n = len(items)
    key_table_off = 7 * 4
    val_table_off = key_table_off + n * 8
    data_off = val_table_off + n * 8

    ids, strs, o_tab, t_tab = b"", b"", [], []
    for k, _ in items:
        o_tab.append((len(k), data_off + len(ids)))
        ids += k + b"\x00"
    tdata_off = data_off + len(ids)
    for _, v in items:
        t_tab.append((len(v), tdata_off + len(strs)))
        strs += v + b"\x00"

    header = struct.pack("<IIIIIII", 0x950412DE, 0, n,
                         key_table_off, val_table_off, 0, 0)
    keys = b"".join(struct.pack("<II", ln, off) for ln, off in o_tab)
    vals = b"".join(struct.pack("<II", ln, off) for ln, off in t_tab)
    return header + keys + vals + ids + strs


def main():
    count = 0
    for po in LOCALE.glob("*/LC_MESSAGES/*.po"):
        entries = parse_po(po.read_text(encoding="utf-8"))
        mo = po.with_suffix(".mo")
        mo.write_bytes(make_mo(entries))
        print(f"compiled {po.relative_to(BASE)} -> {mo.name} ({len(entries)} strings)")
        count += 1
    if not count:
        print("No .po files found under locale/")


if __name__ == "__main__":
    main()
