#include "iw.h"

char *reg_initiator_to_string(__u8 initiator)
{
	switch (initiator) {
	case NL80211_REGDOM_SET_BY_CORE:
		return "the wireless core upon initialization";
	case NL80211_REGDOM_SET_BY_USER:
		return "a user";
	case NL80211_REGDOM_SET_BY_DRIVER:
		return "a driver";
	case NL80211_REGDOM_SET_BY_COUNTRY_IE:
		return "a country IE";
	default:
		return "BUG";
	}
}
