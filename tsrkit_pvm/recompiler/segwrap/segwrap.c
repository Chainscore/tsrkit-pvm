#define _GNU_SOURCE
#include <signal.h>
#include <ucontext.h>
#include <setjmp.h>
#include <stdint.h>
#include <string.h>
#include <stdbool.h>
#include <stddef.h>
#include <sys/mman.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <stdio.h>

static sigjmp_buf jmpbuf;

enum ExitStatus {
  HOST_CALL,
  PAGE_FAULT,
  ILL
};

struct pg_data {
    uint64_t r8,r9,r10,r11,r12,r13,r14,r15;
    uint64_t rdi,rsi,rbp,rbx,rdx,rax,rcx;
    uint64_t rsp, rip, eflags;
    uint64_t si_data;
    enum ExitStatus status;
};

static struct pg_data program_status;
static uint64_t host_call_offset = 1000;
static int syscall_handler_initialized = 0;  // Track initialization state

static void syscall_handler(int sig, siginfo_t *si, void *ctx_) {
  fflush(stdout);
  ucontext_t *uc = (ucontext_t *)ctx_;
#if defined(__x86_64__)
    greg_t *g = uc->uc_mcontext.gregs;
    // NOTE: RCX and R11 gets clobbered during syscall, so we cannot restore their value.
    // For simplicity, we store all regs in memory before syscall and restore from there instead here
    // Save all registers like other handlers to ensure consistency
    program_status.r8  = g[REG_R8];  program_status.r9  = g[REG_R9];
    program_status.r10 = g[REG_R10]; program_status.r11 = g[REG_R11];
    program_status.r12 = g[REG_R12]; program_status.r13 = g[REG_R13];
    program_status.r14 = g[REG_R14]; program_status.r15 = g[REG_R15];
    program_status.rdi = g[REG_RDI]; program_status.rsi = g[REG_RSI];
    program_status.rbp = g[REG_RBP]; program_status.rbx = g[REG_RBX];
    program_status.rdx = g[REG_RDX]; program_status.rax = g[REG_RAX];
    program_status.rcx = g[REG_RCX]; program_status.rsp = g[REG_RSP];
    program_status.rip = g[REG_RIP]; program_status.eflags = g[REG_EFL];
    program_status.si_data = si->si_value.sival_int - host_call_offset;
    program_status.status = HOST_CALL;
#endif
    siglongjmp(jmpbuf, 1);
}

static void sill_handler(int sig, siginfo_t *si, void *ctx) {
    ucontext_t *uc = (ucontext_t *)ctx;
#if defined(__x86_64__)
    greg_t *g = uc->uc_mcontext.gregs;
    program_status.r8  = g[REG_R8];  program_status.r9  = g[REG_R9];
    program_status.r10 = g[REG_R10]; program_status.r11 = g[REG_R11];
    program_status.r12 = g[REG_R12]; program_status.r13 = g[REG_R13];
    program_status.r14 = g[REG_R14]; program_status.r15 = g[REG_R15];
    program_status.rdi = g[REG_RDI]; program_status.rsi = g[REG_RSI];
    program_status.rbp = g[REG_RBP]; program_status.rbx = g[REG_RBX];
    program_status.rdx = g[REG_RDX]; program_status.rax = g[REG_RAX];
    program_status.rcx = g[REG_RCX]; program_status.rsp = g[REG_RSP];
    program_status.rip = g[REG_RIP]; program_status.eflags = g[REG_EFL];
    program_status.si_data = (uint64_t)si->si_addr;
    program_status.status = ILL;
#endif
    siglongjmp(jmpbuf, 1);
}

static void segv_handler(int sig, siginfo_t *si, void *ctx) {
    ucontext_t *uc = (ucontext_t *)ctx;
#if defined(__x86_64__)
    greg_t *g = uc->uc_mcontext.gregs;
    program_status.r8  = g[REG_R8];  program_status.r9  = g[REG_R9];
    program_status.r10 = g[REG_R10]; program_status.r11 = g[REG_R11];
    program_status.r12 = g[REG_R12]; program_status.r13 = g[REG_R13];
    program_status.r14 = g[REG_R14]; program_status.r15 = g[REG_R15];
    program_status.rdi = g[REG_RDI]; program_status.rsi = g[REG_RSI];
    program_status.rbp = g[REG_RBP]; program_status.rbx = g[REG_RBX];
    program_status.rdx = g[REG_RDX]; program_status.rax = g[REG_RAX];
    program_status.rcx = g[REG_RCX]; program_status.rsp = g[REG_RSP];
    program_status.rip = g[REG_RIP]; program_status.eflags = g[REG_EFL];
    program_status.si_data = (uint64_t)si->si_addr;
    program_status.status = PAGE_FAULT;
#endif
    siglongjmp(jmpbuf, 1);
}

int run_code(uint64_t addr, uint64_t *ret_val) {
    if (sigsetjmp(jmpbuf, 1) == 0) {
        uint64_t (*fn)(void) = (uint64_t (*)(void))addr;
        uint64_t r = fn();
        uint64_t return_address;

        //  1) lea the label “1” into return_address  
        //  2) call *fn (which pushes that very address on the stack)  
        //  3) label “1” is where fn() will return to  
        asm volatile(
            "  lea    1f(%%rip), %0\n"
            "  call   *%1\n"
            "1:\n"
            : "=&r"(return_address)       // output #0
            : "r"(fn)                     // input #1
            : "rax", "memory"             // clobberss
        );

        if (ret_val) *ret_val = return_address;
        return 0;   // normal return
    } else {
        return 1;  // segfault
    }
}

int get_program_status(struct pg_data *out) {
    *out = program_status;
    return 0;
}

// --- Handlers --- //
int init_syscall_handler(void) {
    // Check if already initialized
    if (syscall_handler_initialized) {
        return 0;  // Already set up, no need to do it again
    }
    
    fflush(stdout);
    
    // Set up signal handler first
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = syscall_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    
    if (sigaction(SIGSYS, &sa, NULL) == -1) {
        perror("sigaction");
        return -1;
    }
    
    // Prevent gaining new privileges
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == -1) {
        perror("prctl(PR_SET_NO_NEW_PRIVS)");
        return -2;
    }
    
    // Define the BPF filter to trap both Linux syscalls and PVM syscalls
    struct sock_filter filter[] = {
        // Load syscall number
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        
        // Check if syscall number >= 999
        BPF_JUMP(BPF_JMP | BPF_JGE | BPF_K, 999, 0, 2),
        // Check if syscall number <= 1050
        BPF_JUMP(BPF_JMP | BPF_JGT | BPF_K, 1101, 1, 0),
        // If in range [999, 1050], trap it
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_TRAP),
        
        // Allow all other syscalls
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
    
    struct sock_fprog prog = {
        .len = sizeof(filter) / sizeof(filter[0]),
        .filter = filter,
    };
    
    // Install the seccomp filter
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) == -1) {
        perror("prctl(PR_SET_SECCOMP)");
        return -3;
    }
    
    syscall_handler_initialized = 1;  // Mark as initialized
    return 0;
}


int init_segv_handler(void) {
    // --- For SEGV --- // 
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = segv_handler;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigemptyset(&sa.sa_mask);
    int segv_status = sigaction(SIGSEGV, &sa, NULL);  // 0 on success
    return segv_status;
}

int init_segill_handler(void) {
    // --- For SEGILL --- // 
    struct sigaction sill;
    memset(&sill, 0, sizeof(sill));
    sill.sa_sigaction = sill_handler;
    sill.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigemptyset(&sill.sa_mask);
    int sill_status = sigaction(SIGILL, &sill, NULL);  // 0 on success 
    return sill_status;
}

// --- Main Initializer --- // 
int initialize(void) {
  int segv_result = init_segv_handler();
  if (segv_result != 0) return segv_result;
  
  int sill_result = init_segill_handler();  
  if (sill_result != 0) return sill_result;
  
  int syscall_result = init_syscall_handler();
  if (syscall_result != 0) return syscall_result;
  
  return 0;
}

// --- Cleanup Helper --- //
void cleanup(void) {
  signal(SIGSEGV, SIG_DFL);
  signal(SIGILL, SIG_DFL);
  signal(SIGSYS, SIG_DFL);
  syscall_handler_initialized = 0;  // Reset initialization state
}
