#include "allocator_audit.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct { int64_t id; size_t len; char *name; } Record;
int main(void) {
    audit_start();
    Record *rows = malloc(10000 * sizeof(Record));
    if (!rows) return 2;
    for (int i = 0; i < 10000; i++) {
        char text[32];
        int len = snprintf(text, sizeof text, "row-%d", i);
        rows[i] = (Record){i, (size_t)len, malloc((size_t)len)};
        if (!rows[i].name) return 2;
        memcpy(rows[i].name, text, (size_t)len);
    }
    int64_t sum = 0;
    for (int i = 0; i < 10000; i++) {
        sum += rows[i].id + (int64_t)rows[i].len;
        for (size_t j = 0; j < rows[i].len; j++) sum += (unsigned char)rows[i].name[j];
    }
    for (int i = 0; i < 10000; i++) free(rows[i].name);
    free(rows);
    audit_stop();
    printf("%lld\n", (long long)sum);
}
