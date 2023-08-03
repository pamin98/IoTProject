#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc, char ** argv) {
    double num;
    int arg;
    if(argc != 2){
        printf("Invalid use of program.Try ./<name> <float>\n");
        return 1;
    }
    num = atof(argv[1]);
    
    usleep(num * 1000000);
    printf("Slept %f seconds.\n", num);
    
    arg = (42*num);
    if(arg % 2 == 0)
        printf("%d is even.\n", arg);
    else
        printf("%d is odd.\n", arg);
    return 0;
}
