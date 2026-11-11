extern fn audit_start();
extern fn audit_stop();
struct Record { id: i64, name: u8[] }
fn main() {
    audit_start();
    var rows: Record[>..] = [];
    for i in 10000 { rows.push(Record { id: i, name: str("row-", i) }); }
    var checksum: i64 = 0;
    for row in rows {
        checksum += row.id + row.name.len;
        for c in row.name { checksum += c; }
    }
    audit_stop();
    print(checksum);
}
