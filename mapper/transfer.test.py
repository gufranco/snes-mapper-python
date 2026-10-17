import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

INDIRECT_ENABLE = 0x420C


def an_engine(written: dict[int, int]) -> mapper.Engine:
    engine = mapper.Engine()
    for address, value in written.items():
        engine.write(address, value)
    return engine


def a_channel(written: dict[int, int]) -> mapper.Channel:
    channel = mapper.Channel(0)
    for offset, value in written.items():
        channel.write(offset, value)
    return channel


class RegisterTest(unittest.TestCase):
    def test_the_enable_register_belongs_to_the_processor_not_the_display(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(0x420B, 0x01)

        # Assert
        self.assertEqual((mapper.ENABLE, engine.enabled), (0x420B, [0]))

    def test_the_indirect_enable_register_sits_beside_it(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(INDIRECT_ENABLE, 0x81)

        # Assert
        self.assertEqual((engine.enable_indirect, engine.enable), (0x81, 0x00))

    def test_the_channel_registers_start_where_the_processor_puts_them(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(0x4301, 0x18)

        # Assert
        self.assertEqual((mapper.CHANNEL_BASE, engine.channels[0].destination), (0x4300, 0x2118))

    def test_the_channel_registers_are_not_in_the_display_window(self) -> None:
        # Arrange
        display = range(0x2100, 0x2200)

        # Act
        claimed = [address for address in display if mapper.channel_of(address) is not None]

        # Assert
        self.assertEqual(claimed, [])

    def test_a_channel_takes_sixteen_registers(self) -> None:
        # Arrange
        window = range(0x4300, 0x4380)

        # Act
        owners = [mapper.channel_of(address) for address in window]

        # Assert
        self.assertEqual(owners, [index for index in range(8) for _ in range(16)])

    def test_the_last_channel_ends_inside_the_window(self) -> None:
        # Arrange
        last = 0x437F

        # Act
        found = (mapper.channel_of(last), mapper.channel_of(last + 1))

        # Assert
        self.assertEqual(found, (mapper.CHANNEL_COUNT - 1, None))


class ChannelIndexTest(unittest.TestCase):
    def test_an_address_names_the_channel_it_belongs_to(self) -> None:
        # Arrange
        addresses = (0x4300, 0x4370)

        # Act
        found = [mapper.channel_of(address) for address in addresses]

        # Assert
        self.assertEqual(found, [0, 7])

    def test_the_index_comes_from_the_whole_nibble_not_three_bits(self) -> None:
        # Arrange
        address = 0x4380

        # Act
        found = mapper.channel_of(address)

        # Assert
        self.assertIsNone(found)

    def test_an_address_outside_the_window_belongs_to_no_channel(self) -> None:
        # Arrange
        addresses = (0x420B, 0x2100, 0x4200, 0x4400)

        # Act
        found = [mapper.channel_of(address) for address in addresses]

        # Assert
        self.assertEqual(found, [None] * len(addresses))

    def test_every_register_of_a_channel_names_that_channel(self) -> None:
        # Arrange
        registers = range(0x4320, 0x4330)

        # Act
        found = {mapper.channel_of(address) for address in registers}

        # Assert
        self.assertEqual(found, {2})


class ChannelTest(unittest.TestCase):
    def test_a_channel_starts_holding_nothing_it_was_told(self) -> None:
        # Arrange
        index = 0

        # Act
        channel = mapper.Channel(index)

        # Assert
        self.assertEqual((channel.count, bytes(channel.registers)), (0, bytes(16)))

    def test_the_parameters_split_into_direction_and_step(self) -> None:
        # Arrange
        written = {0x00: 0x80}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual((channel.parameters, channel.to_cpu, channel.step), (0x80, True, 1))

    def test_a_fixed_transfer_does_not_advance_its_source(self) -> None:
        # Arrange
        written = {0x00: 0x08}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual(channel.step, 0)

    def test_a_decrementing_transfer_walks_backwards(self) -> None:
        # Arrange
        written = {0x00: 0x10}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual(channel.step, -1)

    def test_the_source_is_assembled_from_three_registers(self) -> None:
        # Arrange
        written = {0x02: 0x34, 0x03: 0x12, 0x04: 0x7E}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual(channel.source, 0x7E1234)

    def test_the_count_is_assembled_from_two_registers(self) -> None:
        # Arrange
        written = {0x05: 0x00, 0x06: 0x08}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual((channel.count, channel.length), (0x0800, 0x0800))

    def test_a_count_of_zero_means_the_whole_range(self) -> None:
        # Arrange
        written: dict[int, int] = {}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual(channel.length, 0x10000)

    def test_the_destination_register_is_kept_low(self) -> None:
        # Arrange
        written = {0x01: 0x18}

        # Act
        channel = a_channel(written)

        # Assert
        self.assertEqual(channel.destination, 0x2118)

    def test_a_channel_plans_what_it_holds(self) -> None:
        # Arrange
        channel = a_channel({0x01: 0x22, 0x02: 0x00, 0x04: 0x7F, 0x05: 0x03})

        # Act
        planned = channel.plan()

        # Assert
        self.assertEqual(
            (planned.channel, planned.source, planned.length, planned.destination),
            (0, 0x7F0000, 3, 0x2122),
        )


class EngineTest(unittest.TestCase):
    def test_an_engine_has_eight_channels(self) -> None:
        # Arrange
        expected = list(range(8))

        # Act
        engine = mapper.Engine()

        # Assert
        self.assertEqual([one.index for one in engine.channels], expected)

    def test_nothing_is_enabled_before_anything_is_asked(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        found = engine.enabled

        # Assert
        self.assertEqual(found, [])

    def test_enabling_a_channel_lists_it(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(mapper.ENABLE, 0x05)

        # Assert
        self.assertEqual(engine.enabled, [0, 2])

    def test_a_channel_that_was_never_configured_is_still_reported_when_enabled(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(mapper.ENABLE, 0x01)

        # Assert
        self.assertEqual(engine.enabled, [0])

    def test_a_configured_channel_that_is_not_enabled_is_left_out(self) -> None:
        # Arrange
        engine = an_engine({0x4302: 0x00, 0x4303: 0x80})

        # Act
        found = engine.plans()

        # Assert
        self.assertEqual((engine.enabled, found), ([], []))

    def test_the_indirect_enable_register_is_kept_apart_from_the_other(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(INDIRECT_ENABLE, 0xC0)

        # Assert
        self.assertEqual((engine.enable_indirect, engine.enable), (0xC0, 0x00))

    def test_arming_indirect_channels_does_not_arm_the_ordinary_ones(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(INDIRECT_ENABLE, 0xFF)

        # Assert
        self.assertEqual(engine.enabled, [])

    def test_a_write_reaches_the_channel_it_addresses(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(0x4321, 0x18)

        # Assert
        self.assertEqual(engine.channels[2].destination, 0x2118)

    def test_a_write_outside_the_window_is_ignored(self) -> None:
        # Arrange
        engine = mapper.Engine()

        # Act
        engine.write(0x2100, 0xFF)

        # Assert
        self.assertEqual(
            [bytes(one.registers) for one in engine.channels], [bytes(16)] * mapper.CHANNEL_COUNT
        )

    def test_a_transfer_reports_what_it_would_move(self) -> None:
        # Arrange
        engine = an_engine(
            {0x4302: 0x00, 0x4303: 0x00, 0x4304: 0x7E, 0x4305: 0x10, 0x4306: 0x00, 0x4301: 0x18}
        )
        engine.write(mapper.ENABLE, 0x01)

        # Act
        planned = engine.plans()

        # Assert
        self.assertEqual(
            [(one.source, one.length, one.destination) for one in planned],
            [(0x7E0000, 0x0010, 0x2118)],
        )

    def test_a_plan_names_the_addresses_a_transfer_would_read(self) -> None:
        # Arrange
        engine = an_engine({0x4304: 0x7E, 0x4305: 0x04, mapper.ENABLE: 0x01})

        # Act
        touched = engine.plans()[0].addresses()

        # Assert
        self.assertEqual(touched, [0x7E0000, 0x7E0001, 0x7E0002, 0x7E0003])

    def test_a_fixed_transfer_reads_one_address_over_and_over(self) -> None:
        # Arrange
        engine = an_engine({0x4300: 0x08, 0x4304: 0x7E, 0x4305: 0x03, mapper.ENABLE: 0x01})

        # Act
        touched = engine.plans()[0].addresses()

        # Assert
        self.assertEqual(touched, [0x7E0000] * 3)

    def test_a_transfer_that_walks_backwards_does_so(self) -> None:
        # Arrange
        engine = an_engine(
            {0x4300: 0x10, 0x4302: 0x10, 0x4304: 0x7E, 0x4305: 0x03, mapper.ENABLE: 0x01}
        )

        # Act
        touched = engine.plans()[0].addresses()

        # Assert
        self.assertEqual(touched, [0x7E0010, 0x7E000F, 0x7E000E])

    def test_a_source_that_runs_off_a_bank_wraps_inside_it(self) -> None:
        # Arrange
        engine = an_engine(
            {0x4302: 0xFF, 0x4303: 0xFF, 0x4304: 0x7E, 0x4305: 0x02, mapper.ENABLE: 0x01}
        )

        # Act
        touched = engine.plans()[0].addresses()

        # Assert
        self.assertEqual(touched, [0x7EFFFF, 0x7E0000])

    def test_a_plan_prints_as_its_channel_and_reach(self) -> None:
        # Arrange
        engine = an_engine({0x4314: 0x7E, 0x4313: 0x80, 0x4315: 0x04, mapper.ENABLE: 0x02})

        # Act
        printed = repr(engine.plans()[0])

        # Assert
        self.assertEqual(printed, "<channel 1: 4 bytes from 7E8000>")


if __name__ == "__main__":
    unittest.main()
