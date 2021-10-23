#!/usr/bin/env python3

import re, sys
from enum import Enum
from .logger import logger

class AssocType(Enum):
    NEW = "new"
    REASSOC = "re-associating"

class _WPAState(Enum):
    DISCONN = "DISCONNECTED"
    SCANNING = "SCANNING"
    AUTHING = "AUTHENTICATING"
    ASSOCING = "ASSOCIATING"
    ASSOCED = "ASSOCIATED"
    FW_HS = "4WAY_HANDSHAKE"
    GRP_HS = "GROUP_HANDSHAKE"
    COMPLETED = "COMPLETED"

class _InfoBlk(object):

    def __init__(self, blk, id_auth_s, id_auth_e, id_assoc_s, id_assoc_e, id_hs_s, id_hs_e, id_conn_s, id_conn_e, is_reassoc):
        self._parse(blk, id_auth_s, id_auth_e, id_assoc_s, id_assoc_e, id_hs_s, id_hs_e, id_conn_s, id_conn_e, is_reassoc)

    def _parse(self, blk, id_auth_s, id_auth_e, id_assoc_s, id_assoc_e, id_hs_s, id_hs_e, id_conn_s, id_conn_e, is_reassoc):
        #essid, bssid, signal_strength, frequency, T_authstart, T_authend, T_assocstart,
        #T_assocend, T_hsstart, T_hsend, T_connstart, T_connend

        #ts, nic, bssid, essid
        bss_re = re.compile(r"^([\.0-9]+):\s*([a-zA-Z0-9_]+):\s*selected\s*BSS\s*([a-zA-Z0-9:]+)\s*ssid=('.*')\s*$")
        level_offset = 2

        #WARNING: This is only used for random ap selection traces, otherwise, the above one is used.
        #bss_re = re.compile(r"^([\.0-9]+):\s*([a-zA-Z0-9_]+):\s*final\sselected\s*BSS\s*([a-zA-Z0-9:]+)\s*ssid=('.*')\s*$")
        #level_offset = 1

        ss_re = re.compile(r"^.*level=([\-0-9]+).*$")
        freq_re = re.compile(r"^[\.0-9]+:\s*[0-9a-zA-Z_]+:\s*SME:.*with\s*([a-zA-Z0-9:]+)\s*.*SSID=('.*')\s*freq=(\d+).*$")
        #find AP selection result
        if not is_reassoc:
            for index in range(id_auth_s, -1, -1):
                match = bss_re.match(blk[index])
                if match:
                    try:
                        self.type = AssocType.NEW
                        self.level = int(ss_re.match(blk[index-level_offset]).group(1))
                    except:
                        logger.error(blk[index-level_offset])
                        raise
        else:
            self.type = AssocType.REASSOC
            self.level = 0

        self.T_auth_s = float(blk[id_auth_s].split(":")[0])
        if id_auth_e:
            self.T_auth_e = float(blk[id_auth_e].split(":")[0])
        else:
            self.T_auth_e = None
        if id_assoc_s:
            self.T_assoc_s = float(blk[id_assoc_s].split(":")[0])
        else:
            self.T_assoc_s = None
        if id_assoc_e:
            self.T_assoc_e = float(blk[id_assoc_e].split(":")[0])
        else:
            self.T_assoc_e = None
        if id_hs_s:
            self.T_hs_s = float(blk[id_hs_s].split(":")[0])
        else:
            self.T_hs_s = None
        if id_hs_e:
            self.T_hs_e = float(blk[id_hs_e].split(":")[0])
        else:
            self.T_hs_e = None
        if id_conn_s:
            self.T_conn_s = float(blk[id_conn_s].split(":")[0])
        else:
            self.T_conn_s = None
        if id_conn_e:
            self.T_conn_e = float(blk[id_conn_e].split(":")[0])
        else:
            self.T_conn_e = None

        freq_re_match = freq_re.match(blk[id_auth_s-1])
        if freq_re_match:
            self.bssid, self.essid, self.freq = freq_re_match.group(1, 2, 3)
            self.freq = int(self.freq)
            self.success = True
        else:
            self.success = False

    def to_list(self):
        return [self.essid, self.bssid, self.level, self.freq, self.T_auth_s, self.T_auth_e, self.T_assoc_s, self.T_assoc_e, self.T_hs_s, self.T_hs_e, self.T_conn_s, self.T_conn_e]

    def __str__(self):
        return "({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})".format(*self.to_list())

class _ParsingState(object):

    def __init__(self):
        self.wpa_state = _WPAState.DISCONN
        self.info_blk = []
        self.info_blk_list = []
        self.completed_blk = False
        self.is_reassoc = True
        self.idx_auth_s = None
        self.idx_auth_e = None
        self.idx_assoc_s = None
        self.idx_assoc_e = None
        self.idx_hs_s = None
        self.idx_hs_e = None
        self.idx_conn_s = None
        self.idx_conn_e = None

    def clear(self):
        self.idx_auth_s = None
        self.idx_auth_e = None
        self.idx_assoc_s = None
        self.idx_assoc_e = None
        self.idx_hs_s = None
        self.idx_hs_e = None
        self.idx_conn_s = None
        self.idx_conn_e = None

class WPAParser(object):

    def __init__(self, wpa_log, intf_list):
        self._wpa_log = wpa_log
        self._intf_list = intf_list

    def parse(self):
        with open(self._wpa_log, "r") as f:
            logger.info("[WPA] Parsing {}".format(self._wpa_log))
            _parsing_states = {intf:_ParsingState() for intf in self._intf_list}
            nic_re = re.compile(r"^[\.0-9]+:\s*([a-zA-Z0-9_]+):.*$")
            #ts, nic, pre_state, post_state
            state_re = re.compile(r"^([\.0-9]+):\s*([a-zA-Z0-9_]+):\s*State:\s*([0-9a-zA-Z_]+)\s*->\s*([0-9a-zA-Z_]+)\s*$")
            for row in f:
                # filter unrelated logs
                match = nic_re.match(row)
                if not match or match.group(1) not in self._intf_list:
                    continue
                intf = match.group(1)
                _ps = _parsing_states[intf]
                _ps.info_blk.append(row)
                match = state_re.match(row)
                if match:
                    try:
                        pre_state = _WPAState(match.group(3))
                        post_state = _WPAState(match.group(4))
                        assert pre_state == _ps.wpa_state
                    except:
                        for row in _ps.info_blk:
                            print(row.strip())
                        print(intf, pre_state, post_state, _ps.wpa_state)
                        raise
                    _ps.wpa_state = post_state
                    if _ps.wpa_state == _WPAState.SCANNING:
                        _ps.is_reassoc = False
                    elif _ps.wpa_state == _WPAState.DISCONN:
                        #if _ps.completed_blk:
                        if _ps.idx_auth_s:
                            if _ps.completed_blk:
                                _ps.idx_conn_e = len(_ps.info_blk) - 1
                            _temp_infoblk = _InfoBlk(_ps.info_blk, _ps.idx_auth_s, _ps.idx_auth_e, _ps.idx_assoc_s, _ps.idx_assoc_e, _ps.idx_hs_s, _ps.idx_hs_e, _ps.idx_conn_s, _ps.idx_conn_e, _ps.is_reassoc)
                            if _temp_infoblk.success:
                                _ps.info_blk_list.append(_temp_infoblk)
                        _ps.completed_blk = False
                        _ps.info_blk = []
                        _ps.is_reassoc = True
                        #for get failed the number of attempts
                        _ps.clear()
                    elif _ps.wpa_state == _WPAState.COMPLETED:
                        if _ps.completed_blk == False:
                            _ps.idx_hs_e = len(_ps.info_blk) - 1
                            _ps.idx_conn_s = len(_ps.info_blk) - 1
                            _ps.completed_blk = True
                    elif _ps.wpa_state == _WPAState.AUTHING:
                        _ps.idx_auth_s = len(_ps.info_blk) - 1
                    elif _ps.wpa_state == _WPAState.ASSOCING:
                        _ps.idx_auth_e = len(_ps.info_blk) - 1
                        _ps.idx_assoc_s = len(_ps.info_blk) - 1
                    elif _ps.wpa_state == _WPAState.ASSOCED:
                        _ps.idx_assoc_e = len(_ps.info_blk) - 1
                        _ps.idx_hs_s = len(_ps.info_blk) - 1

            for intf, _ps in _parsing_states.items():
                logger.info("[WPA ({})] #{} completed connections are founded".format(intf, len(_ps.info_blk_list)))

            return {intf:_ps.info_blk_list for intf, _ps in _parsing_states.items()}

if __name__ == "__main__":
    wpa = WPAParser(sys.argv[1], ["wlp4s0"])
    for k, y in wpa.parse().items():
        for blk in y:
            print (k, ":", blk)

