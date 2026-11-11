#include "allocator_audit.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    audit_start();
    unsigned char *region = malloc(10000 * 48);
    if (!region) return 2;
    size_t top = 0;
    for (int64_t i = 0; i < 10000; i++) {
        char text[32];
        uint32_t len = (uint32_t)snprintf(text, sizeof text, "row-%lld", (long long)i);
        memcpy(region + top, &i, sizeof i); top += sizeof i;
        memcpy(region + top, &len, sizeof len); top += sizeof len;
        memcpy(region + top, text, len); top += len;
    }
    size_t at = 0;
    int64_t sum = 0;
    while (at < top) {
        int64_t id; uint32_t len;
        memcpy(&id, region + at, sizeof id); at += sizeof id;
        memcpy(&len, region + at, sizeof len); at += sizeof len;
        sum += id + len;
        for (uint32_t j = 0; j < len; j++) sum += region[at + j];
        at += len;
    }
    free(region);
    audit_stop();
    printf("%lld\n", (long long)sum);
}
