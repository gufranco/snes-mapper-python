import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import transfer


class RegisterTest(unittest.TestCase):
    def test_the_enable_register_belongs_to_the_processor_not_the_display(self):
        self.assertEqual(transfer.ENABLE, 0x420B)

    def test_the_indirect_enable_register_sits_beside_it(self):
        self.assertEqual(transfer.ENABLE_INDIRECT, 0x420C)

    def test_the_channel_registers_start_where_the_processor_puts_them(self):
        self.assertEqual(transfer.CHANNEL_BASE, 0x4300)

    def test_the_channel_registers_are_not_in_the_display_window(self):
        self.assertFalse(0x2100 <= transfer.ENABLE < 0x2200)
        self.assertFalse(0x2100 <= transfer.CHANNEL_BASE < 0x2200)

    def test_a_channel_takes_sixteen_registers(self):
        self.assertEqual(transfer.CHANNEL_STRIDE, 0x10)

    def test_the_last_channel_ends_inside_the_window(self):
        last = transfer.CHANNEL_BASE + (transfer.CHANNEL_COUNT - 1) * transfer.CHANNEL_STRIDE

        self.assertLess(last + transfer.CHANNEL_STRIDE, 0x4400)


class ChannelIndexTest(unittest.TestCase):
    def test_an_address_names_the_channel_it_belongs_to(self):
        self.assertEqual(transfer.channel_of(0x4300), 0)
        self.assertEqual(transfer.channel_of(0x4370), 7)

    def test_the_index_comes_from_the_whole_nibble_not_three_bits(self):
        self.assertIsNone(transfer.channel_of(0x4380))

    def test_an_address_outside_the_window_belongs_to_no_channel(self):
        for address in (0x420B, 0x2100, 0x4200, 0x4400):
            self.assertIsNone(transfer.channel_of(address))

    def test_every_register_of_a_channel_names_that_channel(self):
        for offset in range(transfer.CHANNEL_STRIDE):
            self.assertEqual(transfer.channel_of(0x4320 + offset), 2)


class ChannelTest(unittest.TestCase):
    def test_a_channel_starts_holding_nothing_it_was_told(self):
        self.assertEqual(transfer.Channel(0).count, 0)

    def test_the_parameters_split_into_direction_and_step(self):
        channel = transfer.Channel(0)
        channel.write(0x00, 0x80)

        self.assertTrue(channel.to_cpu)

    def test_a_fixed_transfer_does_not_advance_its_source(self):
        channel = transfer.Channel(0)
        channel.write(0x00, 0x08)

        self.assertEqual(channel.step, 0)

    def test_a_decrementing_transfer_walks_backwards(self):
        channel = transfer.Channel(0)
        channel.write(0x00, 0x10)

        self.assertEqual(channel.step, -1)

    def test_the_source_is_assembled_from_three_registers(self):
        channel = transfer.Channel(0)
        channel.write(0x02, 0x34)
        channel.write(0x03, 0x12)
        channel.write(0x04, 0x7E)

        self.assertEqual(channel.source, 0x7E1234)

    def test_the_count_is_assembled_from_two_registers(self):
        channel = transfer.Channel(0)
        channel.write(0x05, 0x00)
        channel.write(0x06, 0x08)

        self.assertEqual(channel.count, 0x0800)

    def test_a_count_of_zero_means_the_whole_range(self):
        self.assertEqual(transfer.Channel(0).length, 0x10000)

    def test_the_destination_register_is_kept_low(self):
        channel = transfer.Channel(0)
        channel.write(0x01, 0x18)

        self.assertEqual(channel.destination, 0x2118)


class EngineTest(unittest.TestCase):
    def test_an_engine_has_eight_channels(self):
        self.assertEqual(len(transfer.Engine().channels), transfer.CHANNEL_COUNT)

    def test_nothing_is_enabled_before_anything_is_asked(self):
        self.assertEqual(transfer.Engine().enabled, [])

    def test_enabling_a_channel_lists_it(self):
        engine = transfer.Engine()
        engine.write(transfer.ENABLE, 0x05)

        self.assertEqual(engine.enabled, [0, 2])

    def test_a_channel_that_was_never_configured_is_still_reported_when_enabled(self):
        engine = transfer.Engine()
        engine.write(transfer.ENABLE, 0x01)

        self.assertEqual(engine.enabled, [0])

    def test_a_configured_channel_that_is_not_enabled_is_left_out(self):
        engine = transfer.Engine()
        engine.write(0x4302, 0x00)
        engine.write(0x4303, 0x80)

        self.assertEqual(engine.enabled, [])

    def test_the_indirect_enable_register_is_kept_apart_from_the_other(self):
        engine = transfer.Engine()

        engine.write(transfer.ENABLE_INDIRECT, 0xC0)

        self.assertEqual(engine.enable_indirect, 0xC0)
        self.assertEqual(engine.enable, 0x00)

    def test_arming_indirect_channels_does_not_arm_the_ordinary_ones(self):
        engine = transfer.Engine()

        engine.write(transfer.ENABLE_INDIRECT, 0xFF)

        self.assertEqual(engine.enabled, [])

    def test_a_write_reaches_the_channel_it_addresses(self):
        engine = transfer.Engine()
        engine.write(0x4321, 0x18)

        self.assertEqual(engine.channels[2].destination, 0x2118)

    def test_a_write_outside_the_window_is_ignored(self):
        engine = transfer.Engine()
        engine.write(0x2100, 0xFF)

        self.assertEqual(engine.channels[0].registers[0], 0)

    def test_a_transfer_reports_what_it_would_move(self):
        engine = transfer.Engine()
        engine.write(0x4302, 0x00)
        engine.write(0x4303, 0x00)
        engine.write(0x4304, 0x7E)
        engine.write(0x4305, 0x10)
        engine.write(0x4306, 0x00)
        engine.write(0x4301, 0x18)
        engine.write(transfer.ENABLE, 0x01)

        planned = engine.plan()

        self.assertEqual(len(planned), 1)
        self.assertEqual(planned[0].source, 0x7E0000)
        self.assertEqual(planned[0].length, 0x0010)

    def test_a_plan_names_the_addresses_a_transfer_would_read(self):
        engine = transfer.Engine()
        engine.write(0x4304, 0x7E)
        engine.write(0x4305, 0x04)
        engine.write(transfer.ENABLE, 0x01)

        touched = engine.plan()[0].addresses()

        self.assertEqual(touched, [0x7E0000, 0x7E0001, 0x7E0002, 0x7E0003])

    def test_a_fixed_transfer_reads_one_address_over_and_over(self):
        engine = transfer.Engine()
        engine.write(0x4300, 0x08)
        engine.write(0x4304, 0x7E)
        engine.write(0x4305, 0x03)
        engine.write(transfer.ENABLE, 0x01)

        self.assertEqual(engine.plan()[0].addresses(), [0x7E0000] * 3)

    def test_a_transfer_that_walks_backwards_does_so(self):
        engine = transfer.Engine()
        engine.write(0x4300, 0x10)
        engine.write(0x4302, 0x10)
        engine.write(0x4304, 0x7E)
        engine.write(0x4305, 0x03)
        engine.write(transfer.ENABLE, 0x01)

        self.assertEqual(engine.plan()[0].addresses(), [0x7E0010, 0x7E000F, 0x7E000E])

    def test_a_source_that_runs_off_a_bank_wraps_inside_it(self):
        engine = transfer.Engine()
        engine.write(0x4302, 0xFF)
        engine.write(0x4303, 0xFF)
        engine.write(0x4304, 0x7E)
        engine.write(0x4305, 0x02)
        engine.write(transfer.ENABLE, 0x01)

        self.assertEqual(engine.plan()[0].addresses(), [0x7EFFFF, 0x7E0000])

    def test_a_plan_prints_as_its_channel_and_reach(self):
        engine = transfer.Engine()
        engine.write(transfer.ENABLE, 0x02)

        self.assertIn("channel 1", repr(engine.plan()[0]))


if __name__ == "__main__":
    unittest.main()
