"""Unit tests for fail-closed automation decisions."""
import copy
import unittest

from mforce.controller import SafetyController
from mforce.models import Action, InputError, observation_from_dict
from mforce.scenarios import load_scenarios


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = load_scenarios()

    def _sample(self, name):
        return copy.deepcopy(next(s for s in self.samples if s['id'] == name)['frames'][0])

    def test_hazard_must_stop_before_shift(self):
        sample = self._sample('02_truck_left_verified')
        ctrl = SafetyController()
        self.assertEqual(ctrl.decide(observation_from_dict(sample)).action, Action.WAIT_STOP)

    def test_two_stable_frames_required(self):
        record = self._sample('02_truck_left_verified')
        record['ego_speed_mps'] = 0.0
        ctrl = SafetyController()
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)
        record['event_time_s'] = 2.0
        record['sensor_time_s'] = 2.0
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.CHANGE_LEFT)
        self.assertEqual(ctrl.current_lane, 'left')

    def test_safe_counter_resets_on_obstruction(self):
        record = self._sample('02_truck_left_verified')
        record['ego_speed_mps'] = 0.0
        ctrl = SafetyController()
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)
        record['event_time_s'] = record['sensor_time_s'] = 2.0
        record['lanes']['left']['oncoming'] = True
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)
        record['event_time_s'] = record['sensor_time_s'] = 3.0
        record['lanes']['left']['oncoming'] = False
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)

    def test_fault_is_latched(self):
        record = self._sample('05_sensor_failure')
        ctrl = SafetyController()
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.FAULT_STOP)
        record['event_time_s'] = record['sensor_time_s'] = 2.0
        record['sensor_ok'] = True
        record['obstacle'] = None
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.FAULT_STOP)
        ctrl.reset()
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.CRUISE)

    def test_estop_latched(self):
        record = self._sample('08_emergency_stop')
        ctrl = SafetyController()
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.EMERGENCY_STOP)
        record['emergency_stop'] = False
        record['event_time_s'] = record['sensor_time_s'] = 2.0
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.EMERGENCY_STOP)

    def test_low_confidence_cannot_trigger_lane_change(self):
        record = self._sample('06_low_confidence')
        ctrl = SafetyController()
        for i in range(1,5):
            record['event_time_s'] = record['sensor_time_s'] = float(i)
            self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)

    def test_stale_sample_stops(self):
        record = self._sample('07_stale_sensor')
        self.assertEqual(SafetyController().decide(observation_from_dict(record)).action, Action.FAULT_STOP)

    def test_future_sample_stops(self):
        record = self._sample('01_clear_road')
        record['sensor_time_s'] = record['event_time_s'] + 1.0
        self.assertEqual(SafetyController().decide(observation_from_dict(record)).action, Action.FAULT_STOP)

    def test_replayed_timestamp_stops(self):
        record = self._sample('01_clear_road')
        ctrl = SafetyController()
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.CRUISE)
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.FAULT_STOP)

    def test_no_double_shift(self):
        record = self._sample('02_truck_left_verified')
        record['ego_speed_mps'] = 0.0
        ctrl = SafetyController()
        ctrl.decide(observation_from_dict(record))
        record['event_time_s'] = record['sensor_time_s'] = 2.0
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.CHANGE_LEFT)
        record['event_time_s'] = record['sensor_time_s'] = 3.0
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)

    def test_clear_path_must_be_approved(self):
        record = self._sample('09_unapproved_lane')
        ctrl = SafetyController()
        ctrl.decide(observation_from_dict(record))
        record['event_time_s'] = record['sensor_time_s'] = 2.0
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)

    def test_no_oncoming_in_alternate_lane(self):
        record = self._sample('10_oncoming_lane')
        ctrl = SafetyController()
        ctrl.decide(observation_from_dict(record))
        record['event_time_s'] = record['sensor_time_s'] = 2.0
        self.assertEqual(ctrl.decide(observation_from_dict(record)).action, Action.WAIT_STOP)


class InputValidationTests(unittest.TestCase):
    def setUp(self):
        self.base = copy.deepcopy(next(s for s in load_scenarios() if s['id'] == '01_clear_road')['frames'][0])

    def test_no_missing_lane_data(self):
        del self.base['lanes']['right']
        with self.assertRaises(InputError):
            observation_from_dict(self.base)

    def test_reject_nan(self):
        self.base['ego_speed_mps'] = float('nan')
        with self.assertRaises(InputError):
            observation_from_dict(self.base)

    def test_reject_bool_as_number(self):
        self.base['event_time_s'] = True
        with self.assertRaises(InputError):
            observation_from_dict(self.base)

    def test_reject_out_of_range_confidence(self):
        self.base['lanes']['left']['confidence'] = 1.1
        with self.assertRaises(InputError):
            observation_from_dict(self.base)

    def test_reject_negative_speed(self):
        self.base['ego_speed_mps'] = -1
        with self.assertRaises(InputError):
            observation_from_dict(self.base)

    def test_reject_bad_obstacle_category(self):
        self.base['obstacle'] = {'category': '', 'distance_m': 5, 'confidence': 0.9}
        with self.assertRaises(InputError):
            observation_from_dict(self.base)

    def test_emergency_stop_requires_boolean(self):
        self.base['emergency_stop'] = 'false'
        with self.assertRaises(InputError):
            observation_from_dict(self.base)


if __name__ == '__main__':
    unittest.main()
