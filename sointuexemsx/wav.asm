%define MANGLED
%include TRACK_INCLUDE

%define WAVE_FORMAT_PCM 0x1
%define WAVE_FORMAT_IEEE_FLOAT 0x3
%define FILE_ATTRIBUTE_NORMAL 0x00000080
%define CREATE_ALWAYS 2
%define GENERIC_WRITE 0x40000000

%ifdef USE_4KLANG
	%define LENGTH_IN_SAMPLES MAX_SAMPLES
%else ; USE_4KLANG
	%define LENGTH_IN_SAMPLES SU_LENGTH_IN_SAMPLES
	%ifdef SU_SAMPLE_FLOAT
		%define SAMPLE_FLOAT
	%endif ; SU_SAMPLE_FLOAT
	%define CHANNEL_COUNT SU_CHANNEL_COUNT
	%define SAMPLE_RATE SU_SAMPLE_RATE
	%define SAMPLE_SIZE SU_SAMPLE_SIZE
%endif ; USE_4KLANG

section .bss
sound_buffer:
	resb LENGTH_IN_SAMPLES * SAMPLE_SIZE * CHANNEL_COUNT

file:
	resd 1

bytes_written:
	resd 1

section .data
; Change the filename over -DFILENAME="yourfilename.wav"
filename:
	db FILENAME, 0

; This is the wave file header.
wave_file:
	db "RIFF"
	dd wave_file_end + LENGTH_IN_SAMPLES * SAMPLE_SIZE * CHANNEL_COUNT - wave_file
	db "WAVE"
	db "fmt "
wave_format_end:
	dd wave_format_end - wave_file
%ifdef SAMPLE_FLOAT
	dw WAVE_FORMAT_IEEE_FLOAT
%else ; SAMPLE_FLOAT
	dw WAVE_FORMAT_PCM
%endif ; SAMPLE_FLOAT
	dw CHANNEL_COUNT
	dd SAMPLE_RATE
	dd SAMPLE_SIZE * SAMPLE_RATE * CHANNEL_COUNT
	dw SAMPLE_SIZE * CHANNEL_COUNT
	dw SAMPLE_SIZE * 8
wave_header_end:
	db "data"
	dd wave_file_end + LENGTH_IN_SAMPLES * SAMPLE_SIZE * CHANNEL_COUNT - wave_header_end
wave_file_end:

section .text
symbols:
	extern _CreateFileA@28
	extern _WriteFile@20
	extern _CloseHandle@4
    extern _ExitProcess@4
%ifdef USE_4KLANG
	extern __4klang_render@4
%endif ; USE_4KLANG

	global _mainCRTStartup
_mainCRTStartup:
	; Prologue
	push	ebp
	mov	 ebp, esp
	sub	 esp, 0x10

%ifdef SU_LOAD_GMDLS
	call _su_load_gmdls
%endif ; SU_LOAD_GMDLS

	; We render the complete track here.
	push sound_buffer
%ifdef USE_4KLANG
	call __4klang_render@4
%else ; USE_4KLANG
	call _su_render_song@4
%endif ; USE_4KLANG

	; Now we open the file and save the track.
	push 0x0
	push FILE_ATTRIBUTE_NORMAL
	push CREATE_ALWAYS
	push 0x0
	push 0x0
	push GENERIC_WRITE
	push filename
	call _CreateFileA@28
	mov dword [file], eax

	; This is the WAV header
	push 0x0
	push bytes_written
	push wave_file_end - wave_file
	push wave_file
	push dword [file]
	call _WriteFile@20
	
	; There we write the actual samples
	push 0x0
	push bytes_written
	push LENGTH_IN_SAMPLES * CHANNEL_COUNT * SAMPLE_SIZE
	push sound_buffer
	push dword [file]
	call _WriteFile@20
	
	push dword [file]
	call _CloseHandle@4

exit:
    push 0
    call _ExitProcess@4

	; At least we can skip the epilogue :)
	leave
	ret
