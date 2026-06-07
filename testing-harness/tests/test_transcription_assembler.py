from interviewees.livekit_client import _TranscriptionAssembler


def test_assembler_waits_for_final_flag_across_calls():
    asm = _TranscriptionAssembler()
    assert (
        asm.ingest(segment_id="SG_1", text="Hello ", is_final=False, stream_ended=False)
        is None
    )
    assert asm.ingest(segment_id="SG_1", text="world", is_final=True) == "Hello world"


def test_assembler_stream_ended_delivers_when_final_attr_false():
    """LiveKit agent streams: final=false on open, full text on stream close."""
    asm = _TranscriptionAssembler()
    greeting = "Hi A, I'm Noah, the AI interviewer."
    assert (
        asm.ingest(
            segment_id="SG_73323feb155a",
            text=greeting,
            is_final=False,
            stream_ended=True,
        )
        == greeting
    )


def test_assembler_no_segment_id_treats_as_complete():
    asm = _TranscriptionAssembler()
    assert asm.ingest(segment_id="", text="Done.", is_final=None) == "Done."
