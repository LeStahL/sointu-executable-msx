%define MANGLED
%include TRACK_INCLUDE

%define WAVE_FORMAT_PCM 0x1
%define WAVE_FORMAT_IEEE_FLOAT 0x3
%define WHDR_PREPARED 0x2
%define WAVE_MAPPER 0xFFFFFFFF
%define TIME_SAMPLES 0x2
%define PM_REMOVE 0x1

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

wave_out_handle:
	resd 1

msg:
	resd 1
message:
	resd 7

section .data
wave_format:
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
	dw 0

wave_header:
	dd sound_buffer
	dd LENGTH_IN_SAMPLES * SAMPLE_SIZE * CHANNEL_COUNT
	times 2 dd 0
	dd WHDR_PREPARED
	times 4 dd 0
wave_header_end:

mmtime:
	dd TIME_SAMPLES
sample:
	times 2 dd 0
mmtime_end:

section .text
symbols:
	extern _CreateThread@24
	extern _waveOutOpen@24
	extern _waveOutWrite@12
	extern _waveOutGetPosition@12
	extern _PeekMessageA@20
	extern _TranslateMessage@4
	extern _DispatchMessageA@4
    extern _Sleep@4
%ifdef USE_4KLANG
	extern __4klang_render@4
%endif ; USE_4KLANG
%ifdef SU_LOAD_GMDLS
	extern _su_load_gmdls@0
%endif ; SU_LOAD_GMDLS

	global _mainCRTStartup
_mainCRTStartup:
	; win32 uses the cdecl calling convention. This is more readable imo ;)
	; We can also skip the prologue; Windows doesn't mind.

%ifdef SU_LOAD_GMDLS
	call _su_load_gmdls@0
%endif ; SU_LOAD_GMDLS

	times 2 push 0
	push sound_buffer
%ifdef USE_4KLANG
	lea eax, __4klang_render@4
%else ; USE_4KLANG
	lea eax, _su_render_song@4
%endif ; USE_4KLANG
	push eax
	times 2 push 0
	call _CreateThread@24

%ifdef ADD_DELAY
    ; We can't start playing too early or the missing samples will be audible.
	push DELAY_MS
	call _Sleep@4
%endif ; ADD_DELAY

	; We render in the background while playing already. Fortunately,
	; Windows is slow with the calls below, so we're not worried that
	; we don't have enough samples ready before the track starts.
	times 3 push 0
	push wave_format
	push WAVE_MAPPER
	push wave_out_handle
	call _waveOutOpen@24

	push wave_header_end - wave_header
	push wave_header
	push dword [wave_out_handle]
	call _waveOutWrite@12

	; We need to handle windows messages properly while playing, as waveOutWrite is async.
mainloop:
	dispatchloop:
		push PM_REMOVE
		times 3 push 0
		push msg
		call _PeekMessageA@20
		jz dispatchloop_end

		push msg
		call _TranslateMessage@4

		push msg
		call _DispatchMessageA@4

		jmp dispatchloop
	dispatchloop_end:

	push mmtime_end - mmtime
	push mmtime
	push dword [wave_out_handle]
	call _waveOutGetPosition@12

	; We need to stall here to avoid clicks.
	push 20
	call _Sleep@4

	cmp dword [sample], LENGTH_IN_SAMPLES
	jne mainloop

exit:
	; At least we can skip the epilogue :)
	leave
	ret
