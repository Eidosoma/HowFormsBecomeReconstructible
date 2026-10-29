/* Same left-associated binary64 operations as the frozen NumPy reader.
 * Power is supplied by NumPy; no libm substitute, contraction or fast-math.
 * Input and output arrays must be distinct contiguous buffers (Python checks).
 */
#include <stddef.h>
#include <stdint.h>

void rdt_step(size_t nenv, size_t branches, size_t steps, size_t t,
              size_t settling, double dt, double sigma,
              const double *weights, const double *denominator,
              const double *body, const double *cube, const double *noise,
              const uint8_t *mask, double *out) {
    for (size_t env = 0; env < nenv; ++env) {
        for (size_t branch = 0; branch < branches; ++branch) {
            size_t record = env * branches + branch;
            const double *h = weights + record * 512;
            const double *v = h + 256;
            const double *den = denominator + record * 256;
            for (size_t cue = 0; cue < 2; ++cue) {
                size_t offset = (record * 2 + cue) * 256;
                const double *x = body + offset;
                const double *x3 = cube + offset;
                const double *forcing = noise + ((env * steps + t) * 2 + cue) * 256;
                for (size_t j = 0; j < 256; ++j) {
                    size_t right = (j & 240) | ((j + 1) & 15);
                    size_t left = (j & 240) | ((j + 15) & 15);
                    size_t down = (j + 16) & 255;
                    size_t up = (j + 240) & 255;
                    double incoming = h[j] * x[right] + h[left] * x[left];
                    incoming = incoming + v[j] * x[down];
                    incoming = incoming + v[up] * x[up];
                    double local = den[j] > 0.0 ? incoming / den[j] : 0.0;
                    double self = t >= settling ? x[j] - x3[j] : -x3[j];
                    double drift = self + 2.0 * (local - x[j]);
                    double next = (x[j] + dt * drift) + sigma * forcing[j];
                    if (next < -2.0) next = -2.0;
                    if (next > 2.0) next = 2.0;
                    /* Multiplication preserves negative zero at dead cells. */
                    next = next * (mask[env * 256 + j] ? 0.0 : 1.0);
                    if (j == 113 || j == 114 || j == 129 || j == 130)
                        next = cue == 0 ? 1.0 : -1.0;
                    out[offset + j] = next;
                }
            }
        }
    }
}
