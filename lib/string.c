#include "oomph.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

const char *string_data(struct class_Str s)
{
	return s.buf->data + s.offset;
}

static struct StringBuf *alloc_buf(size_t len)
{
	struct StringBuf *res = malloc(sizeof(*res) + len);
	assert(res);
	res->data = res->flex;
	res->malloced = false;
	res->refcount = 1;
	return res;
}

void string_buf_destructor(void *ptr)
{
	struct StringBuf *buf = ptr;
	if (buf->malloced)
		free((char*)buf->data);
	free(buf);
}

bool meth_Str_equals(struct class_Str a, struct class_Str b)
{
	return (a.nbytes == b.nbytes && memcmp(string_data(a), string_data(b), a.nbytes) == 0);
}

struct class_Str data_to_string(const char *data, size_t len)
{
	struct StringBuf *buf = alloc_buf(len);
	memcpy(buf->flex, data, len);
	return (struct class_Str){ .buf = buf, .nbytes = len, .offset = 0 };
}

struct class_Str cstr_to_string(const char *s)
{
	return data_to_string(s, strlen(s));
}

char *string_to_cstr(struct class_Str s)
{
	if (memchr(string_data(s), '\0', s.nbytes) != NULL)
		panic_printf("zero byte found, can't convert to C string");

	// TODO: optimize?
	char *res = malloc(s.nbytes + 1);
	memcpy(res, string_data(s), s.nbytes);
	res[s.nbytes] = '\0';
	return res;
}

struct class_Str oomph_string_concat(struct class_Str str1, struct class_Str str2)
{
	// TODO: optimize?
	struct StringBuf *buf = alloc_buf(str1.nbytes + str2.nbytes);
	memcpy(buf->flex, string_data(str1), str1.nbytes);
	memcpy(buf->flex + str1.nbytes, string_data(str2), str2.nbytes);
	return (struct class_Str){ .buf = buf, .nbytes = str1.nbytes + str2.nbytes, .offset = 0 };
}

void oomph_string_concat_inplace_cstr(struct class_Str *res, const char *suf)
{
	// TODO: optimize?
	struct class_Str old = *res;
	struct StringBuf *buf = alloc_buf(old.nbytes + strlen(suf));
	memcpy(buf->flex, string_data(old), old.nbytes);
	memcpy(buf->flex + old.nbytes, suf, strlen(suf));
	string_decref(*res);
	*res = (struct class_Str){ .buf = buf, .nbytes = old.nbytes + strlen(suf), .offset = 0 };
}

void oomph_string_concat_inplace(struct class_Str *res, struct class_Str suf)
{
	struct class_Str old = *res;
	*res = oomph_string_concat(*res, suf);
	string_decref(old);
}

// Returns a programmer-readable string, print does not use this
struct class_Str meth_Str_to_string(struct class_Str s)
{
	struct class_Str res = cstr_to_string("\"");
	oomph_string_concat_inplace(&res, s);	// TODO: escape
	oomph_string_concat_inplace_cstr(&res, "\"");
	return res;
}

// example: ONES(6) is 111111 in binary
#define ONES(n) ((1<<(n))-1)

// https://en.wikipedia.org/wiki/UTF-8#Encoding
static bool is_utf8_continuation_byte(unsigned char c)
{
	return (c >> 6 == 1 << 1);  // 10xxxxxx
}
static int parse_utf8_start_byte(unsigned char c)
{
	if (c >> 7 == 0)  // 0xxxxxxx
		return 1;
	if (c >> 5 == ONES(2) << 1)  // 110xxxxx
		return 2;
	if (c >> 4 == ONES(3) << 1)  // 1110xxxx
		return 3;
	if (c >> 3 == ONES(4) << 1)  // 11110xxx
		return 4;
	return -1;
}

bool string_validate_utf8(const char *data, size_t len)
{
	size_t i = 0;
	while(i < len) {
		int n = parse_utf8_start_byte(data[i]);
		if (n == -1 || i+n > len)
			return false;

		i++;
		switch(n){
			case 4:
				if (!is_utf8_continuation_byte(data[i++])) return false;
				// fall through
			case 3:
				if (!is_utf8_continuation_byte(data[i++])) return false;
				// fall through
			case 2:
				if (!is_utf8_continuation_byte(data[i++])) return false;
				// fall through
			case 1:
				break;

			default:
				assert(0);
		}
	}

	assert(i == len);
	return true;
}

// this counts unicode chars, strlen counts utf8 chars
int64_t meth_Str_length(struct class_Str s)
{
	int64_t res = 0;
	size_t i = 0;
	while (i < s.nbytes) {
		int p = parse_utf8_start_byte(string_data(s)[i]);
		assert(p != -1);
		i += p;
		res++;
	}
	assert(i == s.nbytes);
	return res;
}

static struct class_Str slice_from_start(struct class_Str s, size_t len)
{
	assert(s.nbytes >= len);
	incref(s.buf);
	return (struct class_Str){ .buf = s.buf, .nbytes = len, .offset = s.offset };
}

static struct class_Str slice_to_end(struct class_Str s, size_t start)
{
	assert(start <= s.nbytes);
	incref(s.buf);
	return (struct class_Str){ .buf = s.buf, .nbytes = s.nbytes - start, .offset = s.offset + start };
}

struct class_Str oomph_get_first_char(struct class_Str s)
{
	assert(s.nbytes != 0);
	int p = parse_utf8_start_byte(string_data(s)[0]);
	assert(p != -1);
	return slice_from_start(s, p);
}

struct class_Str meth_Str_remove_prefix(struct class_Str s, struct class_Str pre)
{
	if (s.nbytes >= pre.nbytes && memcmp(string_data(s), string_data(pre), pre.nbytes) == 0)
	{
		return slice_to_end(s, pre.nbytes);
	}
	string_incref(s);
	return s;
}

struct class_Str meth_Str_remove_suffix(struct class_Str s, struct class_Str suf)
{
	if (s.nbytes >= suf.nbytes &&
		memcmp(string_data(s) + s.nbytes - suf.nbytes, string_data(suf), suf.nbytes) == 0)
	{
		return slice_from_start(s, s.nbytes - suf.nbytes);
	}
	string_incref(s);
	return s;
}

// python's string.split(sep)[0]
struct class_Str oomph_slice_until_substring(struct class_Str s, struct class_Str sep)
{
	for (size_t i = 0; i + sep.nbytes <= s.nbytes; i++) {
		if (memcmp(string_data(s)+i, string_data(sep), sep.nbytes) == 0)
			return slice_from_start(s, i);
	}
	string_incref(s);
	return s;
}

int64_t oomph_utf8_len(struct class_Str s)
{
	return (int64_t)s.nbytes;
}

int64_t oomph_get_utf8_byte(struct class_Str s, int64_t i)
{
	assert(0 <= i && i < (int64_t)s.nbytes);
	return (unsigned char) string_data(s)[i];
}
