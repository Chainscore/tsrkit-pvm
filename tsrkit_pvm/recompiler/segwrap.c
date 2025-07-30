#define _GNU_SOURCE
#include <signal.h>
#include <ucontext.h>
#include <setjmp.h>
#include <stdint.h>
#include <string.h>
#include <stdbool.h>

static sigjmp_buf jmpbuf;
static volatile int have_fault = 0;

struct regs64 {
    uint64_t r8,r9,r10,r11,r12,r13,r14,r15;
    uint64_t rdi,rsi,rbp,rbx,rdx,rax,rcx;
    uint64_t rsp, rip, eflags;
    uint64_t fault_addr;
    bool seg_fault;
};

static struct regs64 last_regs;

static void sill_handler(int sig, siginfo_t *si, void *ctx) {
    ucontext_t *uc = (ucontext_t *)ctx;
#if defined(__x86_64__)
    greg_t *g = uc->uc_mcontext.gregs;
    last_regs.r8  = g[REG_R8];  last_regs.r9  = g[REG_R9];
    last_regs.r10 = g[REG_R10]; last_regs.r11 = g[REG_R11];
    last_regs.r12 = g[REG_R12]; last_regs.r13 = g[REG_R13];
    last_regs.r14 = g[REG_R14]; last_regs.r15 = g[REG_R15];
    last_regs.rdi = g[REG_RDI]; last_regs.rsi = g[REG_RSI];
    last_regs.rbp = g[REG_RBP]; last_regs.rbx = g[REG_RBX];
    last_regs.rdx = g[REG_RDX]; last_regs.rax = g[REG_RAX];
    last_regs.rcx = g[REG_RCX]; last_regs.rsp = g[REG_RSP];
    last_regs.rip = g[REG_RIP]; last_regs.eflags = g[REG_EFL];
#endif
    siglongjmp(jmpbuf, 1);
}

static void segv_handler(int sig, siginfo_t *si, void *ctx) {
    ucontext_t *uc = (ucontext_t *)ctx;
#if defined(__x86_64__)
    greg_t *g = uc->uc_mcontext.gregs;
    last_regs.r8  = g[REG_R8];  last_regs.r9  = g[REG_R9];
    last_regs.r10 = g[REG_R10]; last_regs.r11 = g[REG_R11];
    last_regs.r12 = g[REG_R12]; last_regs.r13 = g[REG_R13];
    last_regs.r14 = g[REG_R14]; last_regs.r15 = g[REG_R15];
    last_regs.rdi = g[REG_RDI]; last_regs.rsi = g[REG_RSI];
    last_regs.rbp = g[REG_RBP]; last_regs.rbx = g[REG_RBX];
    last_regs.rdx = g[REG_RDX]; last_regs.rax = g[REG_RAX];
    last_regs.rcx = g[REG_RCX]; last_regs.rsp = g[REG_RSP];
    last_regs.rip = g[REG_RIP]; last_regs.eflags = g[REG_EFL];
    last_regs.fault_addr = (uint64_t)si->si_addr;
    last_regs.seg_fault = true;
#endif
    siglongjmp(jmpbuf, 1);
}

int install_seg_handlers(void) {
    // --- For SEGV --- // 
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = segv_handler;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigemptyset(&sa.sa_mask);
    int segv_status = sigaction(SIGSEGV, &sa, NULL);  // 0 on success
    // --- For SEGILL --- // 
    struct sigaction sill;
    memset(&sill, 0, sizeof(sill));
    sill.sa_sigaction = sill_handler;
    sill.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigemptyset(&sill.sa_mask);
    int sill_status = sigaction(SIGILL, &sill, NULL);  // 0 on success 
    return segv_status & sill_status;
}

int run_code(uint64_t addr, uint64_t *ret_val) {
    if (sigsetjmp(jmpbuf, 1) == 0) {
        uint64_t (*fn)(void) = (uint64_t (*)(void))addr;
        uint64_t r = fn();
        if (ret_val) *ret_val = r;
        return 0;  // success
    } else {
        return 1;  // segfault
    }
}

int get_last_regs(struct regs64 *out) {
    *out = last_regs;
    return 0;
}

void cleanup(void) {
  signal(SIGSEGV, SIG_DFL);
}
