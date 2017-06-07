#!/usr/bin/awk

/^\s*$/ {
    next
}

$6 == "00" {
    vid = $6 " " $7 " " $8
    mid = $9 " " $10 " " $11 " " $12
    rest = 18
}

$6 != "00" {
    vid = $6
    mid = $7 " " $8 " " $9 " " $10
    rest = 16
}

{
    mod = ""
    spc = ""
    for( j = rest; j <= NF; ++j ) {
	mod = mod spc $j
	spc = " "
    }
    printf( ",-vendor-,%s,[%s]\n", mod, vid )
    printf( ",-vendor-,%s,[%s]\n", mod, mid )
}
