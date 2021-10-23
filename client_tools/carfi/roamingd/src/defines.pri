DEFINES += \
    _FILE_OFFSET_BITS=64 \
    _GNU_SOURCE \
    _LARGEFILE64_SOURCE \
    HAVE_CHAR16_T \
    HAVE_CHAR32_T \
    HAVE_DECL_COPY_FILE_RANGE=0 \
    HAVE_DECL_GETRANDOM=0 \
    HAVE_DECL_GETTID=0 \
    HAVE_DECL_IFA_FLAGS=1 \
    HAVE_DECL_IFLA_BOND_AD_INFO=1 \
    HAVE_DECL_IFLA_BRIDGE_VLAN_INFO=1 \
    HAVE_DECL_IFLA_BRPORT_LEARNING_SYNC=1 \
    HAVE_DECL_IFLA_BRPORT_PROXYARP=1 \
    HAVE_DECL_IFLA_BR_VLAN_DEFAULT_PVID=1 \
    HAVE_DECL_IFLA_GRE_ENCAP_DPORT=1 \
    HAVE_DECL_IFLA_INET6_ADDR_GEN_MODE=1 \
    HAVE_DECL_IFLA_IPTUN_ENCAP_DPORT=1 \
    HAVE_DECL_IFLA_IPVLAN_MODE=1 \
    HAVE_DECL_IFLA_MACVLAN_FLAGS=1 \
    HAVE_DECL_IFLA_PHYS_PORT_ID=1 \
    HAVE_DECL_IFLA_VLAN_PROTOCOL=1 \
    HAVE_DECL_IFLA_VTI_REMOTE=1 \
    HAVE_DECL_IFLA_VXLAN_REMCSUM_NOPARTIAL=1 \
    HAVE_DECL_KCMP=0 \
    HAVE_DECL_KEYCTL=0 \
    HAVE_DECL_LO_FLAGS_PARTSCAN=1 \
    HAVE_DECL_MEMFD_CREATE=0 \
    HAVE_DECL_NAME_TO_HANDLE_AT=1 \
    HAVE_DECL_NDA_IFINDEX=1 \
    HAVE_DECL_PIVOT_ROOT=0 \
    HAVE_DECL_RENAMEAT2=0 \
    HAVE_DECL_SETNS=1 \
    HAVE_GETTIMEOFDAY \
    HAVE_LINUX_BTRFS_H \
    HAVE_LINUX_MEMFD_H \
    HAVE_SECURE_GETENV \
    HAVE_SYS_AUXV_H \
    SIZEOF_PID_T=4 \
    SIZEOF_UID_T=4 \
    SIZEOF_GID_T=4 \
    SIZEOF_DEV_T=8 \
    SIZEOF_RLIM_T=8

contains(QMAKE_HOST.arch, x86_64) {
    DEFINES += SIZEOF_TIME_T=8
} else {
    DEFINES += SIZEOF_TIME_T=4
}

COMMON_FLAGS = \
    -Wall \
    -Wextra \
    -Wdate-time \
    -Wendif-labels \
    -Wfloat-equal \
    -Wformat=2 \
    -Winit-self \
    -Wlogical-op \
    -Wmissing-include-dirs \
    -Wmissing-noreturn \
    -Wpointer-arith \
    -Wredundant-decls \
    -Wstrict-aliasing=2 \
    -Wundef \
    -Wwrite-strings \
    -Werror=missing-declarations \
    -Werror=return-type \
    -Wno-unused-parameter \
    -fdiagnostics-color \
    -ffast-math \
    -fno-common \
    -fno-strict-aliasing \
    -ffunction-sections \
    -fdata-sections \
    -fPIE \
    -fstack-protector \
    -fstack-protector-strong \
    --param=ssp-buffer-size=4 \
    -fvisibility=hidden

QMAKE_CFLAGS += \
    $$COMMON_FLAGS \
    -Wdeclaration-after-statement \
    -Wnested-externs \
    -Wold-style-definition \
    -Wstrict-prototypes \
    -Werror=implicit-function-declaration \
    -Werror=missing-prototypes \
    -Werror=shadow \
    -Wno-missing-field-initializers \
    -Wno-unused-result \
    -Wno-format-signedness

QMAKE_CXXFLAGS += \
    $$COMMON_FLAGS

QMAKE_LFLAGS += \
    -pie \
    -Wl,--as-needed \
    -Wl,--gc-sections \
    -Wl,--no-undefined \
    -Wl,-fuse-ld=gold \
    -Wl,-z,relro \
    -Wl,-z,now
