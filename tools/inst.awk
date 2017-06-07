#!/usr/bin/awk

/^#/ {
    print
    next
}

$5 == "" {
    # GM
    printf( ",%s,%s,0,0,%s,\n", $2, $3, $4 )
    next
}

$6 == "" {
    # GS, SC, MT
    printf( ",%s,%s,%s,0,%s,\n", $2, $3, $4, $5 )
    next
}

# must be XG
{print}
