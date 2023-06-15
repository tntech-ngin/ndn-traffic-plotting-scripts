'''
    Removes dots from JSON file keys exported from Wireshark 
    NDN dissector. MongoDB does not like dots in keys.
    Usage: python purify.py <path_to_json_file>
    Example: python purify.py file.json
    The new file will be saved as new_file.json
'''

import os
import argparse
import json
from tqdm import tqdm
from settings import LOGGER, NDNPACKETTYPES


class PurifyJSON:
    MISSING = '<MISSING>'

    def __init__(self, file_path):
        self.file_path = file_path

    def _remove_dots_from_key(self, data):
        new_data = {}
        for key, value in data.items():
            new_key = key.replace(".", "_")

            if type(value) is dict:
                new_data[new_key] = self._remove_dots_from_key(value)
            elif type(value) is list:
                new_data[new_key] = []
                for item in value:
                    if type(item) is dict:
                        new_data[new_key].append(
                            self._remove_dots_from_key(item))
                    else:
                        new_data[new_key].append(item)
            else:
                new_data[new_key] = value
        return new_data

    def _write_to_file(self, new_data):
        new_file_path = os.path.join(os.path.dirname(
            self.file_path), "new_" + os.path.basename(self.file_path))
        with open(new_file_path, "w") as json_file:
            json.dump(new_data, json_file, indent=2)

    def process_json_file(self):
        new_file_path = os.path.join(os.path.dirname(
            self.file_path), "new_" + os.path.basename(self.file_path))

        with open(self.file_path, errors='replace') as json_file, open(new_file_path, "a") as new_json_file:
            open_curly_count = 0
            json_obj = ''

            progress_bar = tqdm(desc="Processing packets", unit=" packet")

            for line in json_file:
                line = line.strip()

                r_open_curly = '{' in line
                r_close_curly = '}' in line

                if r_open_curly:
                    open_curly_index = line.find('{')
                    if len(line) - 1 == open_curly_index:
                        open_curly_count += 1

                if r_close_curly:
                    if len(line) in [1, 2]:
                        open_curly_count -= 1

                json_obj += line

                # If first or last line, continue
                if json_obj == '[' or json_obj == ']':
                    json_obj = ''
                    continue

                # If open curly count is 0, we have reached the end of the JSON object
                if open_curly_count == 0 and json_obj != '':
                    json_obj = json_obj.strip(',')

                    try:
                        data = json.loads(json_obj)
                        dot_removed = self._remove_dots_from_key(data)

                        layers = dot_removed['_source'].get('layers', {})

                        # Check if 'ndn_name' is present in 'layers'
                        if 'ndn_name' not in layers:
                            json_obj = ''
                            continue

                        new_data = {
                            'frame_time_epoch': layers['frame_time_epoch'][0],
                        }

                        is_data_packet = 'ndn_data' in layers
                        is_interest_packet = 'ndn_interest' in layers
                        is_nack_packet = 'ndn_nack' in layers

                        if is_nack_packet:
                            new_data.update({
                                'ndn_type': NDNPACKETTYPES.NACK.value,
                                'ndn_nackreason': layers['ndn_nackreason'][0]
                            })

                        elif is_data_packet:
                            new_data.update({
                                'ndn_type': NDNPACKETTYPES.DATA.value,
                                'ndn_name': layers['ndn_name'][0],
                                'ndn_genericnamecomponent': layers['ndn_genericnamecomponent'],
                            })

                            if 'ndn_content' in layers and layers['ndn_content'][0] != PurifyJSON.MISSING:
                                new_data['ndn_content'] = layers['ndn_content'][0]

                            if len(layers['ndn_name']) == 2:
                                new_data['ndn_signaturename'] = layers['ndn_name'][1]
                                for item in new_data['ndn_signaturename'].split('/'):
                                    if item in new_data['ndn_genericnamecomponent']:
                                        new_data['ndn_genericnamecomponent'].remove(
                                            item)

                            if 'ndn_signaturetype' in layers:
                                new_data['ndn_signaturetype'] = layers['ndn_signaturetype'][0]

                        elif is_interest_packet:
                            new_data.update({
                                'ndn_type': NDNPACKETTYPES.INTEREST.value,
                                'ndn_name': layers['ndn_name'][0]
                            })
                            for key in ['ndn_mustbefresh', 'ndn_interestname', 'ndn_canbeprefix', 'ndn_interestlifetime',
                                        'ndn_hoplimit', 'ndn_genericnamecomponent', 'ndn_signaturetype']:
                                if key in layers:
                                    new_data[key] = layers[key] if key in [
                                        'ndn_genericnamecomponent', 'ndn_applicationparameters'] else layers[key][0]

                            if len(layers['ndn_name']) == 2:
                                new_data['ndn_signaturename'] = layers['ndn_name'][1]
                                for item in new_data['ndn_signaturename'].split('/'):
                                    if item in new_data['ndn_genericnamecomponent']:
                                        new_data['ndn_genericnamecomponent'].remove(
                                            item)

                            if 'ndn_applicationparameters' in layers and layers['ndn_applicationparameters'][0] != PurifyJSON.MISSING:
                                new_data['ndn_applicationparameters'] = layers['ndn_applicationparameters'][0]

                        new_json_file.write(json.dumps(new_data))
                        new_json_file.write('\n')
                    except json.decoder.JSONDecodeError as e:
                        LOGGER.error(f'JSONDecodeError: {e}')
                        continue
                    except Exception as e:
                        LOGGER.error(f'Exception: {e}')
                        continue

                    json_obj = ''
                    progress_bar.update()

        json_file.close()
        new_json_file.close()

        LOGGER.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Remove dots from JSON file keys. MongoDB does not like dots in keys.",
        prog='python -m tools.purify')
    parser.add_argument("file_path", type=str, help="Path to the JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        LOGGER.error(f"Error: The file {args.file_path} does not exist.")
        exit(1)

    json_purifier = PurifyJSON(args.file_path)
    json_purifier.process_json_file()
