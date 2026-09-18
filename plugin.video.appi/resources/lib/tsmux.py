"""Minimal MPEG-TS stream-copy muxer for separate HLS video/audio renditions."""

PACKET_SIZE = 188
AUDIO_TYPES = {0x03, 0x04, 0x0F, 0x11, 0x81, 0x87}


def _packets(data):
    if not data:
        return []
    start = data.find(b'\x47')
    while start >= 0 and start + PACKET_SIZE < len(data):
        if data[start + PACKET_SIZE] == 0x47:
            break
        start = data.find(b'\x47', start + 1)
    if start < 0:
        raise ValueError('MPEG-TS sync byte was not found')
    usable = (len(data) - start) // PACKET_SIZE * PACKET_SIZE
    return [bytearray(data[pos:pos + PACKET_SIZE]) for pos in range(start, start + usable, PACKET_SIZE)]


def _pid(packet):
    return ((packet[1] & 0x1F) << 8) | packet[2]


def _payload_offset(packet):
    control = (packet[3] >> 4) & 0x03
    if control not in (1, 3):
        return None
    offset = 4
    if control == 3:
        offset += 1 + packet[4]
    return offset if offset < PACKET_SIZE else None


def _section(packets, wanted_pid):
    value = bytearray()
    expected = None
    collecting = False
    for packet in packets:
        if _pid(packet) != wanted_pid:
            continue
        offset = _payload_offset(packet)
        if offset is None:
            continue
        if packet[1] & 0x40:
            pointer = packet[offset]
            offset += 1 + pointer
            value = bytearray()
            expected = None
            collecting = True
        if not collecting or offset >= PACKET_SIZE:
            continue
        value.extend(packet[offset:])
        if expected is None and len(value) >= 3:
            expected = 3 + (((value[1] & 0x0F) << 8) | value[2])
        if expected is not None and len(value) >= expected:
            return bytes(value[:expected])
    raise ValueError('MPEG-TS PSI section {} was not found'.format(wanted_pid))


def _program(packets):
    pat = _section(packets, 0)
    if not pat or pat[0] != 0:
        raise ValueError('Invalid MPEG-TS programme association table')
    end = len(pat) - 4
    for offset in range(8, end, 4):
        number = (pat[offset] << 8) | pat[offset + 1]
        pid = ((pat[offset + 2] & 0x1F) << 8) | pat[offset + 3]
        if number:
            return number, pid
    raise ValueError('MPEG-TS contains no selectable programme')


def _pmt(packets, pmt_pid):
    section = _section(packets, pmt_pid)
    if not section or section[0] != 2:
        raise ValueError('Invalid MPEG-TS programme map')
    program_number = (section[3] << 8) | section[4]
    pcr_pid = ((section[8] & 0x1F) << 8) | section[9]
    info_length = ((section[10] & 0x0F) << 8) | section[11]
    program_info = section[12:12 + info_length]
    streams = []
    offset = 12 + info_length
    end = len(section) - 4
    while offset + 5 <= end:
        stream_type = section[offset]
        pid = ((section[offset + 1] & 0x1F) << 8) | section[offset + 2]
        length = ((section[offset + 3] & 0x0F) << 8) | section[offset + 4]
        descriptors = section[offset + 5:offset + 5 + length]
        streams.append((stream_type, pid, descriptors))
        offset += 5 + length
    return program_number, pcr_pid, program_info, streams


def _crc32_mpeg(data):
    crc = 0xFFFFFFFF
    for value in data:
        crc ^= value << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
    return crc.to_bytes(4, 'big')


def _pat_section(program_number, pmt_pid):
    section = bytearray((0x00, 0xB0, 0x0D, 0x00, 0x01, 0xC1, 0x00, 0x00))
    section.extend((program_number >> 8, program_number & 0xFF, 0xE0 | (pmt_pid >> 8), pmt_pid & 0xFF))
    section.extend(_crc32_mpeg(section))
    return bytes(section)


def _pmt_section(program_number, pcr_pid, program_info, streams):
    body = bytearray((
        program_number >> 8, program_number & 0xFF, 0xC1, 0x00, 0x00,
        0xE0 | (pcr_pid >> 8), pcr_pid & 0xFF,
        0xF0 | (len(program_info) >> 8), len(program_info) & 0xFF,
    ))
    body.extend(program_info)
    for stream_type, pid, descriptors in streams:
        body.extend((
            stream_type, 0xE0 | (pid >> 8), pid & 0xFF,
            0xF0 | (len(descriptors) >> 8), len(descriptors) & 0xFF,
        ))
        body.extend(descriptors)
    section_length = len(body) + 4
    section = bytearray((0x02, 0xB0 | (section_length >> 8), section_length & 0xFF))
    section.extend(body)
    section.extend(_crc32_mpeg(section))
    return bytes(section)


def _psi_packets(pid, section):
    packets = []
    remaining = b'\x00' + section
    first = True
    while remaining:
        chunk, remaining = remaining[:184], remaining[184:]
        header = bytearray((0x47, (0x40 if first else 0) | (pid >> 8), pid & 0xFF, 0x10))
        packets.append(header + bytearray(chunk) + bytearray(b'\xFF' * (184 - len(chunk))))
        first = False
    return packets


def _pts(packet):
    offset = _payload_offset(packet)
    if offset is None or offset + 14 > PACKET_SIZE or packet[offset:offset + 3] != b'\x00\x00\x01':
        return None
    flags = (packet[offset + 7] >> 6) & 0x03
    if flags not in (2, 3):
        return None
    value = packet[offset + 9:offset + 14]
    return (
        ((value[0] >> 1) & 0x07) << 30 |
        value[1] << 22 | (value[2] >> 1) << 15 |
        value[3] << 7 | value[4] >> 1
    )


def _groups(packets, allowed, pid_map=None):
    pid_map = pid_map or {}
    active = {}
    result = []
    last_pts = {}
    for packet in packets:
        source_pid = _pid(packet)
        if source_pid not in allowed:
            continue
        output_pid = pid_map.get(source_pid, source_pid)
        packet[1] = (packet[1] & 0xE0) | ((output_pid >> 8) & 0x1F)
        packet[2] = output_pid & 0xFF
        if packet[1] & 0x40:
            if output_pid in active:
                result.append(active.pop(output_pid))
            timestamp = _pts(packet)
            if timestamp is None:
                timestamp = last_pts.get(output_pid, 0)
            last_pts[output_pid] = timestamp
            active[output_pid] = [timestamp, output_pid, [packet]]
        elif output_pid in active:
            active[output_pid][2].append(packet)
    result.extend(active.values())
    return result


def _write_packet(output, packet, continuity):
    pid = _pid(packet)
    control = (packet[3] >> 4) & 0x03
    counter = continuity.get(pid, 0)
    packet[3] = (packet[3] & 0xF0) | counter
    if control in (1, 3):
        continuity[pid] = (counter + 1) & 0x0F
    output.write(packet)


def mux_segments(video_paths, audio_paths, target):
    """Mux aligned MPEG-TS HLS rendition segments without decoding media."""
    if not video_paths or not audio_paths:
        raise ValueError('Separate HLS video/audio rendition is empty')
    first_video = _packets(open(video_paths[0], 'rb').read())
    first_audio = _packets(open(audio_paths[0], 'rb').read())
    program_number, pmt_pid = _program(first_video)
    _, pcr_pid, program_info, video_streams = _pmt(first_video, pmt_pid)
    _, audio_pmt_pid = _program(first_audio)
    _, _, _, source_audio_streams = _pmt(first_audio, audio_pmt_pid)
    source_audio_streams = [value for value in source_audio_streams if value[0] in AUDIO_TYPES]
    if not source_audio_streams:
        raise ValueError('Separate HLS audio rendition contains no supported audio stream')
    used = {pid for _, pid, _ in video_streams} | {0, pmt_pid, pcr_pid}
    pid_map = {}
    next_pid = 0x110
    audio_streams = []
    for stream_type, source_pid, descriptors in source_audio_streams:
        output_pid = source_pid
        if output_pid in used:
            while next_pid in used:
                next_pid += 1
            output_pid = next_pid
            next_pid += 1
        used.add(output_pid)
        pid_map[source_pid] = output_pid
        audio_streams.append((stream_type, output_pid, descriptors))
    pat = _psi_packets(0, _pat_section(program_number, pmt_pid))
    pmt = _psi_packets(
        pmt_pid, _pmt_section(program_number, pcr_pid, program_info, video_streams + audio_streams)
    )
    video_pids = {pid for _, pid, _ in video_streams}
    audio_pids = {pid for _, pid, _ in source_audio_streams}
    continuity = {}

    def track_groups(paths, allowed, mapping=None):
        for path in paths:
            groups = _groups(_packets(open(path, 'rb').read()), allowed, mapping)
            groups.sort(key=lambda value: (value[0], value[1]))
            for group in groups:
                yield group

    video_groups = iter(track_groups(video_paths, video_pids))
    audio_groups = iter(track_groups(audio_paths, audio_pids, pid_map))
    video_group = next(video_groups, None)
    audio_group = next(audio_groups, None)
    with open(target, 'wb') as output:
        for packet in pat + pmt:
            _write_packet(output, bytearray(packet), continuity)
        while video_group is not None or audio_group is not None:
            if audio_group is None or (
                    video_group is not None and
                    (video_group[0], video_group[1]) <= (audio_group[0], audio_group[1])):
                group = video_group
                video_group = next(video_groups, None)
            else:
                group = audio_group
                audio_group = next(audio_groups, None)
            for packet in group[2]:
                _write_packet(output, packet, continuity)
    return target
