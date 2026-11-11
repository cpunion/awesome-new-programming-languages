#ifndef ALLOCATOR_AUDIT_H
#define ALLOCATOR_AUDIT_H
#include <stddef.h>
#include <stdlib.h>
#include <sys/mman.h>

void audit_start(void);
void audit_stop(void);
void *audit_malloc(size_t);
void *audit_calloc(size_t, size_t);
void *audit_realloc(void *, size_t);
void audit_free(void *);
void *audit_mmap(void *, size_t, int, int, int, off_t);

#ifndef AUDIT_IMPLEMENTATION
#define malloc audit_malloc
#define calloc audit_calloc
#define realloc audit_realloc
#define free audit_free
#define mmap audit_mmap
#endif
#endif
