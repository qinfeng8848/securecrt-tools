# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
import csv

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import utilities

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    | SINGLE device script
    | Morphed: Gordon Rogier grogier@cisco.com
    | Framework: Jamie Caesar jcaesar@presidio.com

    This script will capture the WLC AireOS wlan & remote-lan & guest-lan details and returns an output list

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["AireOS"])

    # Get additional information we'll need
    get_wlan_detail(session, to_cvs=True)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


def get_wlan_detail(session, to_cvs=False):
    """
    A function that captures the WLC AireOS wlan & remote-lan & guest-lan details and returns an output list

    :param session: The script object that represents this script being executed
    :type session: session.Session

    :return: A list of wlan details
    :rtype: list of lists
    """

    # Get the show wlan summary
    send_cmd = "show wlan summary"
    raw_wlan_summary = session.get_command_output(send_cmd)
    # Get the show remote-lan summary
    send_cmd = "show remote-lan summary"
    raw_rlan_summary = session.get_command_output(send_cmd)
    # Get the show guest-lan summary
    send_cmd = "show guest-lan summary"
    raw_glan_summary = session.get_command_output(send_cmd)

    template_file = session.script.get_template("cisco_aireos_show_wlan_summary.template")
    wlan_summary_dict = utilities.textfsm_parse_to_dict(raw_wlan_summary, template_file)
    rlan_summary_dict = utilities.textfsm_parse_to_dict(raw_rlan_summary, template_file)
    glan_summary_dict = utilities.textfsm_parse_to_dict(raw_glan_summary, template_file)

    output_raw = ''
    output_list = []
    for wlan_entry in wlan_summary_dict:
        send_cmd = "show wlan " + format(wlan_entry["WLAN_Identifier"])
        output_list.append(session.get_command_output(send_cmd))

    raw_rlan_detail = ''
    for wlan_entry in rlan_summary_dict:
        send_cmd = "show remote-lan " + format(wlan_entry["WLAN_Identifier"])
        output_list.append(session.get_command_output(send_cmd))

    raw_glan_detail = ''
    for wlan_entry in glan_summary_dict:
        send_cmd = "show guest-lan " + format(wlan_entry["WLAN_Identifier"])
        output_list.append(session.get_command_output(send_cmd))

    output = []
    first = True
    for output_raw in output_list:
        # TextFSM template for parsing "show wlan <WLAN-ID>" output
        template_file = session.script.get_template("cisco_aireos_show_wlan_detail.template")
        if first:
            output = utilities.textfsm_parse_to_list(output_raw, template_file, add_header=True)
            first = False
        else:
            output.append(utilities.textfsm_parse_to_list(output_raw, template_file, add_header=False)[0])

    if to_cvs:
        output_filename = session.create_output_filename("wlan-detail", ext=".csv")
        utilities.list_of_lists_to_csv(output, output_filename)

    return output


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Get session object for the SecureCRT tab that the script was launched from.
    crt_session = crt_script.get_main_session()
    # Run script's main logic against our session
    try:
        script_main(crt_session)
    except Exception:
        crt_session.end_cisco_session()
        raise
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
