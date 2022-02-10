from libc.stdlib cimport free
 
cpdef void free_(unsigned char *n):
    free(n)
    
