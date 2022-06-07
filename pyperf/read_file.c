#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned long long int readen(char *path) {
    char *line = NULL;
    size_t len = 0;
    ssize_t read;
    unsigned long long int data;

    FILE *fd = fopen(path, "r");

    if (fd == NULL)
      exit(EXIT_FAILURE);

    while ((read = getline(&line, &len, fd)) != -1) {
      //Do nothing.
    }

    data = strtoull(line, NULL, 10);

    if (line)
      free(line);

    fclose(fd);

    return data;  
}
