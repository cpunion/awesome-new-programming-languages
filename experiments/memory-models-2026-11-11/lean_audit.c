#include <lean/lean.h>
/* Lean's bundled C environment supplies lean.h but no stdio.h. */
extern int printf(const char *, ...);
size_t audit_ctor_calls;
lean_obj_res audit_lean_start(void) {
    audit_ctor_calls = 0;
    return lean_io_result_mk_ok(lean_box(0));
}
lean_obj_res audit_lean_stop(lean_obj_arg keep, uint64_t checksum) {
    size_t count = audit_ctor_calls;
    int shared = !lean_is_scalar(keep);
    size_t original_sum = 0;
    for (lean_object *cursor = keep; !lean_is_scalar(cursor); cursor = lean_ctor_get(cursor, 1))
        original_sum += lean_unbox(lean_ctor_get(cursor, 0));
    printf("{\"retained_original\":%s,\"generated_ctor_calls\":%zu,\"checksum\":%llu,\"original_checksum\":%zu}\n",
        shared ? "true" : "false", count, (unsigned long long)checksum, original_sum);
    lean_dec(keep);
    return lean_io_result_mk_ok(lean_box(0));
}
