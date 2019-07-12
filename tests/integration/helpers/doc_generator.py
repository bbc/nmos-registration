import re
from random import randint
import rstr

node_format = {
    'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    'version': re.compile('^[0-9]+:[0-9]+$'),
    'label': 'String Name',
    'description': 'A longer string describing things and stuff',
    'tags': {},
    'href': 'uri',
    'caps': {},
    'api': {
        'versions': [re.compile('^v[0-9]+\.[0-9]+$')],
        'endpoints': [{
            'host': '172.0.0.1',
            'port': 1000,
            'protocol': 'http' 
        }]
    },
    'services': [{
        'href': 'uri',
        'type': 'uri',
    }],
    'interfaces': [{
        'chassis_id': re.compile('^([0-9a-f]{2}[-]){5}([0-9a-f]{2})$'),
        'port_id': re.compile('([0-9a-f]{2}[-]){5}([0-9a-f]{2})$'),
        'name': 'String Name'
    }],
    'clocks': [{
        'name': re.compile('clk[0-9]'),
        'ref_type': 'internal'
    }],
}

device_format = {
    'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    'version': re.compile('^[0-9]+:[0-9]+$'),
    'label': 'String Name',
    'description': 'A longer string describing things and stuff',
    'tags': {},
    'type': re.compile('urn:x-nmos:device:(pipeline|generic)'),
    'node_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    'senders': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
    'receivers': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
    'controls': [{
        'href': 'uri',
        'type': 'uri',
    }]
}

source_format = {
    'audio': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'caps': {},
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')], # relates to grains (and possibly flows)
        'clock_name': re.compile('clk[0-9]'),
        'format': 'urn:x-nmos:format:audio',
        'channels': [{
            'label': 'String Name',
            'symbol': ('L','R','C','LFE','Ls','Rs','Lss','Rss','Lrs','Rrs','Lc','Rc','Cs','HI','VIN','M1','M2','Lt','Rt','Lst','Rst','S', re.compile('NSC(0[0-9]{2}|1[0-1]{1}[0-9]{1}|12[0-7]{1})'), re.compile('U(0[1-9]{1}|[1-5]{1}[0-9]{1}|6[0-4]{1})'))
        }]
    },
    'generic': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'caps': {},
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')], # relates to grains (and possibly flows)
        'clock_name': re.compile('clk[0-9]'),
        'format': re.compile('urn:x-nmos:format:(video|data|mux)')
    },
}

flow_format = {
    'video_raw': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:video',
        'frame_width': 0,
        'frame_height': 0,
        'interlace_mode': ('progressive', 'interlaced_tff', 'interlaced_bff', 'interlaced_psf'),
        'colorspace': ('BT601', 'BT709', 'BT2020', 'BT2100'),
        'transfer_characteristic': ('SDR', 'HLG', 'PQ'),
        'media_type': 'video/raw',
        'components': [{
            'name': ('Y','Cb','Cr','I','Ct','Cp','A','R','G','B','DepthMap'),
            'width': 0,
            'height': 0,
            'bit_depth': 0,
        }]
    },
    'video_coded': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:video',
        'frame_width': 0,
        'frame_height': 0,
        'interlace_mode': ('progressive', 'interlaced_tff', 'interlaced_bff', 'interlaced_psf'),
        'colorspace': ('BT601', 'BT709', 'BT2020', 'BT2100'),
        'transfer_characteristic': ('SDR', 'HLG', 'PQ'),
        'media_type': ('video/H264', 'video/vc2'),
    },
    'audio_raw': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:audio',
        'sample_rate': {
            'numerator': 0,
            'denominator': 1,
        },
        'media_type': ('audio/L24', 'audio/L20', 'audio/L16', 'audio/L8'),
        'bit_depth': 0,
    },
    'audio_coded': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:audio',
        'sample_rate': {
            'numerator': 0,
            'denominator': 1,
        },
        'media_type': re.compile('^audio\\/[^\\s\\/]+$')
    },
    'data': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:data',
        'media_type': re.compile('^[^\\s\\/]+\\/[^\\s\\/]+$'),
    },
    'sdicanc_data': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:data',
        'media_type': 'video/smpte291',
        'DID_SDID': {
            'DID': re.compile('^0x[0-9a-fA-F]{2}$'),
            'SDID': re.compile('^0x[0-9a-fA-F]{2}$'),
        },
    },
    'mux': {
        'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'version': re.compile('^[0-9]+:[0-9]+$'),
        'label': 'String Name',
        'description': 'A longer string describing things and stuff',
        'tags': {},
        'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'parents': [re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
        'grain_rate': {
            'numerator': 0,
            'demoninator': 1,
        },
        'format': 'urn:x-nmos:format:mux',
        'media_type': 'video/SMPTE2022-6',
    },
}

sender_format = {
    'id': re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    'version': re.compile('^[0-9]+:[0-9]+$'),
    'label': 'String Name',
    'description': 'A longer string describing things and stuff',
    'tags': {},
    'flow_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    'transport': re.compile('urn:x-nmos:transport:(rtp|rtp.ucast|rtp.mcast|dash)'),
    'device_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    'manifest_href': 'uri',
    'interface_bindings': ['str'],
    'subscription': {
        'receiver_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'active': True
    },
}

def generate_list(input_list, val_count):
    output = []
    for ii in range(0,val_count):
        for value in input_list:
            if type(value) is str:
                output.append(value)
            elif type(value) is int:
                if value < 100:
                    output[key] = randint(0,100)
                else:
                    output.append(value)
            elif type(value) is dict:
                output.append(generate_object(value))
            else:
                try:
                    if len(value.pattern) > 0:
                        output.append(rstr.xeger(value))
                except AttributeError:
                    continue
    return output

def generate_object(input_object):
    output = {}
    for key, value in input_object.items():
        if type(value) is str:
            output[key] = value
        elif type(value) is int:
            if value < 100:
                output[key] = randint(0,100)
            else:
                output[key] = value
        elif type(value) is tuple:
            chosen = value[randint(0, len(value)-1)]
            generate_item(chosen)
        elif type(value) is list:
            val_count = randint(1,5)
            output[key] = []
            for index in range(0, val_count):
                index_output = 'None'
                if type(value[0]) is dict:
                    output[key].append(generate_object(value[0]))
                else:
                    output[key] = generate_list(value, val_count)
        elif type(value) is dict:
            output[key] = generate_object(value)
        elif type(value) is bool:
            output[key] = True if randint(0,1) == 1 else False
        else:
                try:
                    if len(value.pattern) > 0:
                        output[key] = rstr.xeger(value)
                except AttributeError:
                    continue
    return output

def generate_item(input_item):
    if type(input_item) is str:
        return input_item
    elif type(input_item) is int:
        if input_item < 100:
            return randint(0,100)
        else:
            return input_item
    elif type(input_item) is tuple:
        chosen = input_item[randint(0, len(input_item)-1)]
        return generate_item(chosen)
    elif type(input_item) is list:
        val_count = randint(1,5)
        output = []
        for index in range(0, val_count):
            if type(input_item[0]) is dict:
                output.append(generate_object(input_item[0]))
            else:
                output.append(generate_list(input_item))
        return output
    elif type(input_item) is dict:
        return generate_object(input_item)


def generate_node():
    return generate_object(node_format)
            
def generate_device():
    return generate_object(device_format)

def generate_source():
    source_types = list(source_format.keys())
    source_type = source_types[randint(0, len(source_types) - 1)]
    return generate_object(source_format[source_type])

def generate_sender():
    return generate_object(sender_format)

def generate_flow():
    flow_types = list(flow_format.keys())
    flow_type = flow_types[randint(0, len(flow_types) - 1)]
    return generate_object(flow_format[flow_type])

def generate_source_with_flows(flow_count=0):
    source_types = list(source_format.keys())
    source_type = source_types[randint(0, len(source_types) - 1)]
    source = generate_object(source_format[source_type])

    flows = []
    number_flows = flow_count if flow_count > 0 else randint(0,10)

    for ii in range(0,number_flows):
        flow_types = list(flow_format.keys())
        flow_type = flow_types[randint(0, len(flow_types) - 1)]
        flow = generate_object(flow_format[flow_type])
        flow['source_id'] = source['id']
        flows.append(flow)

    flow_keys = [flow['id'] for flow in flows]
    source['parents'] = flow_keys

    return source, flows

def generate_source_with_flows_and_devices(flow_count=0):
    source_types = list(source_format.keys())
    source_type = source_types[randint(0, len(source_types) - 1)]
    source = generate_object(source_format[source_type])

    flows = []
    number_flows = flow_count if flow_count > 0 else randint(1,5)

    device = generate_device()

    for ii in range(0,number_flows):
        flow_types = list(flow_format.keys())
        flow_type = flow_types[randint(0, len(flow_types) - 1)]
        flow = generate_object(flow_format[flow_type])
        flow['source_id'] = source['id']
        flow['device_id'] = device['id']
        flows.append(flow)

    flow_keys = [flow['id'] for flow in flows]
    source['parents'] = flow_keys
    source['device_id'] = device['id']


    return source, flows, device

def generate_device_with_senders_sources_and_flows(flow_count=0):
    device = generate_device()

    number_senders = randint(1,5)
    senders = []
    from_sender_to_device = []
    
    for ii in range(0,number_senders):
        sender = generate_sender()
        sender['device_id'] = device['id']
        senders.append(sender)
        from_sender_to_device.append([sender['id'], sender['device_id']])

    sender_ids = [sender['id'] for sender in senders]
    device['senders'] = sender_ids

    number_flows = flow_count if flow_count > 0 else randint(1,5)
    flows = []
    sources = []
    from_flow_to_device = []
    from_source_to_device = []
    from_flow_to_source = []
    for ii in range(0, number_flows):
        source_types = list(source_format.keys())
        source_type = source_types[randint(0, len(source_types) - 1)]
        source = generate_object(source_format[source_type])
        source['device_id'] = device['id']
        sources.append(source)
        from_source_to_device.append([source['id'], source['device_id']])
        # source['parents'] array might include flow, spec references grains only

        flow_types = list(flow_format.keys())
        flow_type = flow_types[randint(0, len(flow_types) - 1)]
        flow = generate_object(flow_format[flow_type])
        flow['source_id'] = source['id']
        flow['device_id'] = device['id']
        from_flow_to_device.append([flow['id'], flow['device_id']])
        from_flow_to_source.append([flow['id'], flow['source_id']])
        flows.append(flow)

    return device, senders, sources, flows, from_sender_to_device, from_source_to_device, from_flow_to_device, from_flow_to_source