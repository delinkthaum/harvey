""" get_node_status.py -- Helper function to pull status data for the Teztools node.

    Language: Python 3.9
"""

import json
import logging

import requests


def get_node_info(
    status_url: str,
    node_name: str,
    node_field: str = "name",
    slice_field: str = "nodes",
) -> dict:
    """Pull status of the node based on site response data, assuming that status_url
    contains JSON node data.

    Parameters
    ----------
    status_url: str
        URL to pull from.
    node_name: str
        Name of the node.
    node_field: str
        Name field for node info.
        (Optional) Defaults to: "name"
    slice_field: str
        Top-level field to slice JSON response to before looking for node_name in
        node_field. If None, don't perform a slice.
        (Optional) Defaults to: "nodes"

    Returns
    ----------
    dict
        Node status info. For the original use case, expected fields include:
            name
            sync_state
            diskpct
            version
            updated
        If a non-200 code is received from the site, return an empty dict.
    """
    logging.debug(f"Pulling JSON data from site '{status_url}'.")
    resp = requests.get(status_url)
    if resp.status_code != 200:
        logging.error(f"Failed to pull data. Site response: '{resp.status_code}'.")
        return dict()
    table = json.loads(resp.content)
    table = table[slice_field] if slice_field else table
    # Node info should only appear once, so pulling the first matching record is safe.
    node_info = next((i for i in table if i[node_field] == node_name), dict())
    if not node_info:
        logging.error(
            f"Info for node '{node_name}' not found - no matching value in field "
            f"'{node_field}'."
        )
    else:
        logging.info(f"Successfully pulled data for node '{node_name}'.")
    return node_info
