#define AUDIT_IMPLEMENTATION
#include "allocator_audit.h"
#include <stdio.h>

static size_t mallocs, callocs, reallocs, frees, mappings, requested, mapped;

void *audit_malloc(size_t n) { mallocs++; requested += n; return malloc(n); }
void *audit_calloc(size_t n, size_t s) { callocs++; requested += n * s; return calloc(n, s); }
void *audit_realloc(void *p, size_t n) { reallocs++; requested += n; return realloc(p, n); }
void audit_free(void *p) { frees++; free(p); }
void *audit_mmap(void *p, size_t n, int prot, int flags, int fd, off_t offset) {
    mappings++; mapped += n;
    return mmap(p, n, prot, flags, fd, offset);
}
static void report(const char *phase) {
    fprintf(stderr, "{\"phase\":\"%s\",\"malloc_calls\":%zu,\"calloc_calls\":%zu,"
        "\"realloc_calls\":%zu,\"free_calls\":%zu,\"mmap_calls\":%zu,"
        "\"requested_bytes\":%zu,\"mapped_virtual_bytes\":%zu}\n",
        phase, mallocs, callocs, reallocs, frees, mappings, requested, mapped);
}
void audit_start(void) {
    report("startup");
    mallocs = callocs = reallocs = frees = mappings = requested = mapped = 0;
}
void audit_stop(void) { report("work"); }
