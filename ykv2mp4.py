import os
import json
from urllib.parse import unquote
import subprocess
import sys
import shutil

temp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')

def read_last_bytes(input_file, num_bytes):
	with open(input_file, 'rb') as f:
		f.seek(-num_bytes, 2)
		return f.read()

def unpack_files(packed_file, output_path):
	last_16_bytes = read_last_bytes(packed_file, 16)
	size_info = last_16_bytes.decode('utf-8').strip()

	size_to_skip = int(size_info.split('\x00')[0].strip())

	with open(packed_file, 'rb') as f:
		f.seek(-(16 + size_to_skip), 2)
		json_data = f.read(size_to_skip)

	decoded_json = unquote(json_data.decode('utf-8'))
	files_info = json.loads(decoded_json)

	info_input_file = os.path.join(output_path, 'info.json')
	with open(info_input_file, 'w', encoding='utf-8') as info_f:
		json.dump(files_info, info_f, indent=2)

	count = 0

	with open(packed_file, 'rb') as packed_f:
		for file_info in files_info:
			filename = file_info['name']
			if filename == 'dbInfo':
				break
			offset = file_info['offset']
			size = file_info['size']

			packed_f.seek(offset)
			content = packed_f.read(size)

			if content[:2] == b'YK':
				content = content[34:]	# Skip the first 34 bytes
				count+=1
				type = filename.split('.')[-1]

			output_file = os.path.join(output_path, filename)
			with open(output_file, 'wb') as out_f:
				out_f.write(content)

	return count, type

def ykv2mp4(input_file, output_file):
	count, type = unpack_files(input_file, temp_folder)

	os.makedirs(os.path.dirname(output_file), exist_ok=True)

	ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'ffmpeg')
	concat = 'concat:'
	for i in range(1, count+1):
		concat += os.path.join(temp_folder, f'{i}.{type}|')
	args = ['-i', concat, '-c', 'copy', '-y', output_file]
	subprocess.run([ffmpeg_path] + args)

def process_folder(input_folder, output_folder):
	for entry in os.scandir(input_folder):
		if entry.is_file():
			if entry.name.endswith(".ykv"):
				print(entry.path)
				output_file = os.path.join(output_folder, entry.name.replace('.ykv', '.mp4'))
				if os.path.exists(output_file):
					print('Skipped')
				else:
					ykv2mp4(entry.path, output_file)
		elif entry.is_dir():
			process_folder(entry.path, os.path.join(output_folder, entry.name))

def main():
	os.makedirs(temp_folder, exist_ok=True)

	if os.path.isfile(sys.argv[1]):
		for i in sys.argv[1:]:
			name = os.path.basename(sys.argv[1]).replace('.ykv', '.mp4')
			output_folder = os.path.join(os.path.dirname(sys.argv[1]), 'out')
			os.makedirs(output_folder, exist_ok=True)
			ykv2mp4(i, os.path.join(output_folder, name))
	else:
		input_folder = sys.argv[1]
		output_folder = sys.argv[2]
		os.makedirs(output_folder, exist_ok=True)
		process_folder(input_folder, output_folder)

	print('Done.')

	shutil.rmtree(temp_folder)

if __name__ == "__main__":
	main()
