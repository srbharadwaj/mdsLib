import logging
import re

from .connection_manager.errors import CLIError
from .constants import SHUTDOWN, NO_SHUTDOWN, PAT_FC
from .interface import Interface
from .nxapikeys import interfacekeys
from .utility.allexceptions import InvalidAnalyticsType, InvalidInterface

log = logging.getLogger(__name__)


class Fc(Interface):
    """
    Fc interface module
    extends Interface module

        :param switch: switch object
        :type switch: Switch
        :param name: name of fc interface
        :type name: str
        :raises InvalidInterface: when interface name is incorrect while creating object
        :example:
            >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")

    """

    def __init__(self, switch, name):
        fcmatch = re.match(PAT_FC, name)
        if not fcmatch:
            raise InvalidInterface(
                "Interface name " + str(
                    name) + " is not correct, name must be 'fc' interface. Example: 'fc1/2'.. fcobj = Fc(switch_obj,'fc1/2') ")
        super().__init__(switch, name)
        self.__swobj = switch

    # property for out_of_service
    def _set_out_of_service(self, value):
        if type(value) is not bool:
            raise TypeError("Only bool value(true/false) supported.")
        cmd = "terminal dont-ask ; interface " + self.name + " ; out-of-service force ; no terminal dont-ask "
        if value:
            # First shutdown the port then
            self.status = SHUTDOWN
            self.__swobj.config(cmd)
        else:
            cmd = cmd.replace("out-of-service", "no out-of-service")
            self.__swobj.config(cmd)
            self.status = NO_SHUTDOWN

    # out_of_service property
    out_of_service = property(fset=_set_out_of_service)
    """
    set out-of-service configuration for the fc interface

    :param value: set to True to enable out-of-service, False otherwise
    :type value: bool
    :example:
            >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
            >>> fcobj.out-of-service = True
            >>>
    """

    @property
    def transceiver(self):
        """
        Returns handler for transceiver module, using which we could do transceiver related operations

        :return: transceiver handler
        :rtype: Transceiver
        :example:
            >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
            >>> trans_handler = fcobj.transceiver
            >>>
        """

        return self.Transceiver(self)

    @property
    def analytics_type(self):
        """
        get analytics type on the fc interface or
        set analytics type on the fc interface

        :getter:
        :return: analytics type on the interface, None if there are no analytics configs
        :rtype: str
        :example:
            >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
            >>> print(fcobj.analytics_type)
            scsi
            >>>

        :setter:
        :param type: set analytics type on the fc interface
        :type type: str
        :values: scsi/nvme/all/None . Setting the value to None will remove the analytics config on the interface
        :example:
            >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
            >>> fcobj.analytics_type = 'scsi'
            scsi
            >>>

        """
        is_scsi = False
        is_nvme = False
        pat = "analytics type fc-(.*)"
        cmd = "show running-config interface " + self.name + " | grep analytics "
        out, error = self.__swobj._ssh_handle.show(cmd)
        if len(error) != 0:
            raise CLIError(cmd, error)
        else:
            for eachline in out:
                newline = eachline.strip().strip("\n")
                m = re.match(pat, newline)
                if m:
                    type = m.group(1)
                    if type == 'scsi':
                        is_scsi = True
                    if type == 'nvme':
                        is_nvme = True
        if is_scsi:
            if is_nvme:
                return 'all'
            else:
                return 'scsi'
        elif is_nvme:
            return 'nvme'
        else:
            return None

    @analytics_type.setter
    def analytics_type(self, type):
        if type is None:
            cmd = "no analytics type fc-all"
        elif type == 'scsi':
            cmd = "no analytics type fc-all ; analytics type fc-scsi"
        elif type == 'nvme':
            cmd = "no analytics type fc-all ; analytics type fc-nvme"
        elif type == 'all':
            cmd = "analytics type fc-all"
        else:
            raise InvalidAnalyticsType(
                "Invalid analytics type '" + type + "'. Valid types are scsi,nvme,all,None(to disable analytics type)")

        cmdtosend = "interface " + self.name + " ; " + cmd
        out, error = self.__swobj._ssh_handle.config(cmdtosend)
        if len(error) != 0:
            raise CLIError(cmd, error)

    def _execute_transceiver_cmd(self):
        result = {}
        cmd = "show interface " + self.name + " transceiver detail"
        log.debug("Sending the cmd")
        log.debug(cmd)
        out = self.__swobj.config(cmd)['body']['TABLE_interface_trans']['ROW_interface_trans']['TABLE_calib'][
            'ROW_calib']
        if type(out) is list:
            for d in out:
                result.update(d)
        else:
            result = out
        log.debug(result)
        return result

    class Transceiver(object):
        """
        Transceiver module

        :param fcobj: Fc interface object
        :type fcobj: Fc

        """

        def __init__(self, fcobj):
            self.__fcobj = fcobj

        @property
        def sfp_present(self):
            """
            Returns if sfp is present on the Fc interface

            :return: True if sfp is present, False otherwise
            :rtype: bool
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.sfp_present)
                True
                >>>
            """

            out = self.__fcobj._execute_transceiver_cmd()
            retout = out.get(interfacekeys.SFP)
            return ("sfp is present" in retout)

        @property
        def name(self):
            """
            Returns the name of the sfp if present

            :return: the name of the sfp if present, None otherwise
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.name)
                CISCO-FINISAR
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            return out.get(interfacekeys.NAME, None)

        @property
        def part_number(self):
            """
            Returns the part number of the sfp if present

             :return: the part number of the sfp if present
             :rtype: str
             :example:
                 >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                 >>> trans_handler = fcobj.transceiver
                 >>> print(trans_handler.part_number)
                 FTLF8532P4BCV-C1
                 >>>
             """
            out = self.__fcobj._execute_transceiver_cmd()
            return out.get(interfacekeys.PART_NUM, None)

        @property
        def cisco_id(self):
            """
            Returns the cisco-id of the sfp if present

            :return: the cisco-id of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.cisco_id)
                SFP-H10GB-CU3M (0x81)
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            return out.get(interfacekeys.CISCO_ID, None)

        @property
        def cisco_part_number(self):
            """
            Returns the cisco part number of the sfp if present

            :return: the cisco part number of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.cisco_part_number)
                10-3206-01
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            return out.get(interfacekeys.CISCO_PART_NUM, None)

        @property
        def cisco_product_id(self):
            """
            Returns the cisco product id of the sfp if present

            :return: the cisco product id of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.cisco_product_id)
                DS-SFP-FC32G SW
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            return out.get(interfacekeys.CISCO_PRODUCT_ID, None)

        @property
        def bit_rate(self):
            """
            Returns the bit rate of the sfp if present

            :return: the bit rate of the sfp if present
            :rtype: int
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.bit_rate)
                28000
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            return out.get(interfacekeys.BIT_RATE, None)

        @property
        def min_speed(self):
            """
            Returns the min speed of the sfp if present

            :return: the min speed of the sfp if present
            :rtype: int
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.min_speed)
                8000
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            supp_speed = out.get(interfacekeys.SUPP_SPEED, None)
            if supp_speed is not None:
                pat = "Min speed: (\d+) Mb/s, Max speed: (\d+) Mb/s"
                match = re.match(pat, supp_speed)
                if match:
                    return match.group(1)
            return None

        @property
        def max_speed(self):
            """
            Returns the max speed of the sfp if present

            :return: the max speed of the sfp if present
            :rtype: int
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.max_speed)
                32000
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            supp_speed = out.get(interfacekeys.SUPP_SPEED, None)
            if supp_speed is not None:
                pat = "Min speed: (\d+) Mb/s, Max speed: (\d+) Mb/s"
                match = re.match(pat, supp_speed)
                if match:
                    return match.group(2)
            return None

        @property
        def temperature(self):
            """
            Returns the temperature of the sfp if present

            :return: the temperature of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.temperature)
                47.65 C
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            try:
                calibdetails = out['TABLE_calibration']['ROW_calibration']['TABLE_detail']['ROW_detail']
                return calibdetails.get(interfacekeys.TEMPERATURE, None)
            except KeyError:
                return None

        @property
        def voltage(self):
            """
            Returns the voltage of the sfp if present

            :return: the voltage of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.voltage)
                3.39 V
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            try:
                calibdetails = out['TABLE_calibration']['ROW_calibration']['TABLE_detail']['ROW_detail']
                return calibdetails.get(interfacekeys.VOLTAGE, None)
            except KeyError:
                return None

        @property
        def current(self):
            """
            Returns the current of the sfp if present

            :return: the current of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.current)
                7.79 mA
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            try:
                calibdetails = out['TABLE_calibration']['ROW_calibration']['TABLE_detail']['ROW_detail']
                return calibdetails.get(interfacekeys.CURRENT, None)
            except KeyError:
                return None

        @property
        def tx_power(self):
            """
            Returns the tx_power of the sfp if present

            :return: the tx_power of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.tx_power)
                -0.88 dBm
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            try:
                calibdetails = out['TABLE_calibration']['ROW_calibration']['TABLE_detail']['ROW_detail']
                return calibdetails.get(interfacekeys.TX_POWER, None)
            except KeyError:
                return None

        @property
        def rx_power(self):
            """
            Returns the rx_power of the sfp if present

            :return: the rx_power of the sfp if present
            :rtype: str
            :example:
                >>> fcobj = Fc(switch = switch_obj, name = "fc1/1")
                >>> trans_handler = fcobj.transceiver
                >>> print(trans_handler.rx_power)
                -10.66 dBm
                >>>
            """
            out = self.__fcobj._execute_transceiver_cmd()
            try:
                calibdetails = out['TABLE_calibration']['ROW_calibration']['TABLE_detail']['ROW_detail']
                return calibdetails.get(interfacekeys.RX_POWER, None)
            except KeyError:
                return None
