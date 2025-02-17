#include "oomph.h"
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>

noreturn void panic_printf_errno(const char *fmt, ...)
{
	int er = errno;

	// Make sure that what is printed here goes after everything else
	fflush(stdout);
	fflush(stderr);

	va_list ap;
	va_start(ap, fmt);
	vfprintf(stderr, fmt, ap);
	va_end(ap);

	if (er)
		fprintf(stderr, " (errno %d: %s)", er, strerror(er));
	fputc('\n', stderr);

	exit(1);
}

void oomph_assert(bool cond, struct class_Str path, int64_t lineno)
{
	if (!cond)
		panic_printf("assert() failed in \"%s\", line %d", string_to_cstr(path), (int)lineno);
}

static int global_argc = -1;
static const char *const *global_argv = NULL;

int64_t oomph_argv_count(void)
{
	assert(global_argc != -1);
	return global_argc;
}

struct class_Str oomph_argv_get(int64_t i)
{
	assert(global_argv != NULL);
	assert(0 <= i && i < global_argc);
	return cstr_to_string(global_argv[i]);
}


void oomph_main(void);
int main(int argc, char **argv) {
	global_argc = argc;
	global_argv = (const char*const*)argv;
	oomph_main();
	return 0;
}
