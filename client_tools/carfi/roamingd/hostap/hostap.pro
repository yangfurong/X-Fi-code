TEMPLATE = aux

wpas.commands = $(MAKE) -C wpa_supplicant
QMAKE_EXTRA_TARGETS += wpas

PRE_TARGETDEPS += wpas
