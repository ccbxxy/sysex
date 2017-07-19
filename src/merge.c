/* merge.c -
 *  merge MIDI streams
 *
 *  merge source ... dest
 */

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <stdint.h>
#include <time.h>
#include <stdbool.h>

#define IS_CHANNEL(b)  ((b) & 0x80)
#define IS_SYSRT(b)    ((b) & 0xF8)
#define IS_SYSTEM(b)   ((b) & 0xF0)
#define IS_SOX(b)      ((b) == 0xF0)
#define IS_EOX(b)      ((b) == 0xF7)

static const int MAX_STREAMS = 8;

static uint8_t msglen[16] = {
    /* system common messages (0xFn), low nybble */
    [0x00] = 0,			/* SOX                          */
    [0x01] = 1,			/* MTC QF,   0nnndddd           */
    [0x02] = 2,			/* SPP,      0lo byte, 0hi byte */
    [0x03] = 1,			/* Song Sel, 0sssssss           */
    [0x04] = 0,			/* Undefined                    */
    [0x05] = 0,			/* Undefined                    */
    [0x06] = 0,			/* Tune Request                 */
    [0x07] = 0,			/* EOX                          */
    /* channel messages, high nybble */
    [0x08] = 2,			/* note off, 0kkkkkkk, 0vvvvvvv */
    [0x09] = 2,			/* note on,  0kkkkkkk, 0vvvvvvv */
    [0x0A] = 2,			/* poly AT,  0kkkkkkk, 0vvvvvvv */
    [0x0B] = 2,			/* CC,       0ccccccc, 0vvvvvvv */
    [0x0C] = 1,			/* PC,       0ppppppp           */
    [0x0D] = 1,			/* Chan AT,  0vvvvvvv           */
    [0x0E] = 2,			/* p bend,   0lo byte, 0hi byte */
    [0x0F] = 0			/* System, handled separately   */
};

typedef struct _State {
    pthread_mutex_t lock;
    pthread_mutex_t lock_rt;
    uint8_t         status;
    int             fd;
} State;

#define LOCK   pthread_mutex_lock
#define UNLOCK pthread_mutex_unlock

typedef struct _IOStatus {
    int retval;
    int error;
} IOStatus;

typedef struct _MIDIStream {
    int       fd;		/* input FD.  wrap for LV2 later */
    int       out_fd;		/* shared among all instances    */
    char     *name;
    int       id;		/* unique non-tid identifier     */
    bool      done;
    bool      joined;
    pthread_t tid;
    IOStatus  io;		/* IO result info                */
    State     *global;		/* shared state                  */
} MIDIStream;


static void
putbyte(MIDIStream *mss, uint8_t byte) {

    if( (mss->io.retval = write(mss->global->fd, &byte, 1)) != 0 ) {
	mss->io.error = errno;
	mss->done = true;
	pthread_exit(mss);
    }
}

static uint8_t
getbyte(MIDIStream *mss) {
    uint8_t byte;

    if( (mss->io.retval = read(mss->fd, &byte, 1)) <= 0 ) {
	mss->io.error = errno;
	mss->done = true;
	pthread_exit(mss);
    }
    return byte;
}

static void
putmsg(MIDIStream *mss, uint8_t status, uint8_t byte, int count) {
    /* lock held */

    int i = 0;
    if( byte == status ) {
	/* message starts with status byte and is the same
	 *  status as the last message from this input.  Can we
	 *  drop it for running status?
	 */
	if( mss->global->status != status ) {
	    /* nope. some other thread has written a message with
	     *  a different status
	     *
	     * note: if another thread wrote a message with the same
	     *  status as ours, we will follow as running status
	     */
	    putbyte(mss, byte);
	    mss->global->status = byte;
	}
	i = 0;
    }
    else {
	/* message starts with non-status byte
	 *  did another thread get in a message since we last
	 *  emitted our status?
	 */
	if( mss->global->status != status ) {
	    putbyte(mss, status);
	    mss->global->status = status;
	}
	putbyte(mss, byte);
	++i;
    }
    while( i <= count ) {
	byte = getbyte(mss);
	if( IS_CHANNEL(byte) ) {
	    /* incomplete message... what to do
	     */
	    mss->io.error = EINVAL;
	    mss->io.retval = -1;
	    mss->done = true;
	    pthread_exit(mss);
	}
	putbyte(mss, byte);
	if( !IS_SYSRT(byte) ) {
	    ++i;
	}
    }
}


static void *
run(void *arg) {
    MIDIStream      *mss = (MIDIStream *) arg;
    uint8_t          byte, status = 0x00;
    pthread_mutex_t *lockp = &mss->global->lock;
    pthread_mutex_t *rtlockp = &mss->global->lock_rt;
    int              count;

    for(;;) {
	byte = getbyte(mss);
	if( IS_SYSRT(byte) ) {
	    /* we can insert realtime messages without a lock
	     *  I've chosen to lock realtime messages out of SYSEX
	     *  transfers.
	     */
	    LOCK(rtlockp); {
		putbyte(mss, byte);
	    } UNLOCK(rtlockp);
	    continue;
	}
	
	LOCK(lockp); {
	    if( IS_SOX(byte) ) {
		/* F0 ... F7.  Lock out everybody.  GIGO.
		 */
		LOCK(rtlockp); {
		    do {
			putbyte(mss, byte);
			byte = getbyte(mss);
		    } while( !IS_EOX(byte) );
		    putbyte(mss, byte);
		    mss->global->status = 0x00;
		} UNLOCK(rtlockp);
	    }
	    else if( IS_SYSTEM(byte) ) {
		count = msglen[byte & 0x0F];
		putmsg(mss, status, byte, count);
		status = byte;
	    }
	    else if( IS_CHANNEL(byte) ) {
		count = msglen[byte >> 4];
		putmsg(mss, status, byte, count);
		status = byte;
	    }
	    else {
		/* running status */
		putmsg(mss, status, byte, count);
	    }
	} UNLOCK(lockp);
    }
}

int
mss_init(MIDIStream *mss, int flags) {
    int fd = open(mss->name, flags);
    mss->io = (IOStatus) {.error = 0, .retval = 0};
    mss->joined = mss->done = false;
    return fd;
}

int
main(int argc, char *argv[]) {

    State global = {
	.lock    = PTHREAD_MUTEX_INITIALIZER,
	.lock_rt = PTHREAD_MUTEX_INITIALIZER,
	.status  = 0x00,
	.fd      = -1
    };
    MIDIStream mss[MAX_STREAMS];
    int i, j, out = 0;
    int fd;
    
    for(i = 1; i <= argc; ++i) {
	j = i-1;
	if( j > MAX_STREAMS ) {
	    printf( "max input streams is %d\n", MAX_STREAMS-1 );
	    exit(1);
	}
	mss[j].name = argv[i];
	mss[j].id = j;
	if( i == argc ) {
	    if( (fd = mss_init(&mss[j], O_WRONLY)) < 0 ) {
		printf( "cannot open %s (%s)\n",
			argv[i], strerror(errno) );
		exit(1);
	    }
	    global.fd = fd;
	    out = j;
	}
	else {
	    if( (fd = mss_init(&mss[j], O_RDONLY)) < 0 ) {
		printf( "cannot open %s (%s)\n",
			argv[i], strerror(errno) );
		exit(1);
	    }
	    mss[j].fd = fd;
	    mss[j].global = &global;
	}
    }
    if( out == 0 ) {
	//usage();
	exit(1);
    }
    
    /* launch the threads */
    int s;
    for( i = 0; i < out; ++i ) {
	s = pthread_create(&mss[i].tid, NULL, &run, &mss[i]);
    }

    MIDIStream *result;
    bool done = false;
    while( !done ) {
	done = true;
	for( i = 0; i < out; ++i ) {
	    if( mss[i].joined ) {
		continue;
	    }
	    if( mss[i].done ) {
		s = pthread_join(mss[i].tid, NULL);
		mss[i].joined = true;
	    }
	    else {
		done = false;
		usleep(250000);
	    }
	}
    }
}

