#include <lean/lean.h>
extern size_t audit_ctor_calls;
static inline lean_object *audit_alloc_ctor(unsigned tag, unsigned objects, unsigned bytes) {
    audit_ctor_calls++;
    return lean_alloc_ctor(tag, objects, bytes);
}
#define lean_alloc_ctor audit_alloc_ctor
