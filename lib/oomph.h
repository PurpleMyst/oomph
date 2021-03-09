#ifndef LIB_H
#define LIB_H

#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <string.h>

#define REFCOUNT_HEADER int64_t refcount;

struct class_Str {
	REFCOUNT_HEADER
	char str[];   // flexible array member, ends with \0, valid utf-8
};
struct class_Str *cstr_to_string(const char *s);
void string_concat_inplace(struct class_Str **res, const char *suf);
bool string_validate_utf8(const char *s);
#define dtor_Str free
struct class_List_Str;

noreturn void panic_printf(const char *fmt, ...);

// Currently it's not easy to return a list of strings from C function
int64_t argv_count(void);
struct class_Str *argv_get(int64_t i);

struct class_Str *io_read_file(const struct class_Str *path);
void io_mkdir(const struct class_Str *path);
void io_print(const struct class_Str *s);
void io_write_file(const struct class_Str *path, const struct class_Str *content);
void oomph_assert(bool cond, int64_t lineno);
int64_t string_find_internal(const struct class_Str *s, const struct class_Str *sub);
int64_t subprocess_run(void *args);

#define meth_Str_equals(a, b) (strcmp((a)->str, (b)->str) == 0)
#define meth_bool_equals(a, b) ((a)==(b))
#define meth_float_equals(a, b) ((a)==(b))
#define meth_int_equals(a, b) ((a)==(b))
double meth_Str_to_float(const struct class_Str *s);
int64_t meth_Str_length(const struct class_Str *s);
int64_t meth_Str_to_int(const struct class_Str *s);
int64_t meth_Str_unicode_length(const struct class_Str *s);
int64_t meth_float_ceil(double d);
int64_t meth_float_floor(double d);
int64_t meth_float_round(double d);
int64_t meth_float_truncate(double d);
struct class_Str *meth_Str_slice(const struct class_Str *s, int64_t start, int64_t end);
struct class_Str *meth_Str_to_string(struct class_Str *s);
struct class_Str *meth_float_to_string(double d);
struct class_Str *meth_int_to_string(int64_t n);

/*
Can't be macros because of assumptions that compiler makes:
- Can be used in comma expressions, as in (decref(ptr), (ptr = new_value))
- Only evaluates argument once
*/
void incref(void *ptr);
void decref(void *ptr, void (*destructor)(void *ptr));

// Special functions. Keep up to date with typer.py.
#define bool_not(a) (!(a))
#define float_add(a, b) ((a)+(b))
#define float_div(a, b) ((a)/(b))
#define float_gt(a, b) ((a)>(b))
#define float_mul(a, b) ((a)*(b))
#define float_neg(a) (-(a))
#define float_sub(a, b) ((a)-(b))
#define int2float(x) ((double)(x))
#define int_add(a, b) ((a)+(b))
#define int_gt(a, b) ((a)>(b))
#define int_mul(a, b) ((a)*(b))
#define int_neg(a) (-(a))
#define int_sub(a, b) ((a)-(b))
double float_mod(double a, double b);
int64_t int_mod(int64_t a, int64_t b);
struct class_Str *string_concat(const struct class_Str *str1, const struct class_Str *str2);

#endif   // LIB_H
