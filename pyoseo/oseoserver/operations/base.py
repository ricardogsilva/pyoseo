# Copyright 2014 Ricardo Garcia Silva
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Base classes for the OSEO operations
"""

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings as django_settings
import pyxb
import pyxb.bundles.opengis.oseo_1_0 as oseo

from oseoserver import models

class OseoOperation(object):
    """
    This is the base class for OSEO operations.

    It should not be instantiated directly
    """

    NAME = None  # to be reimplemented in child classes

    def _get_delivery_options(self, db_item):
        """
        Return the delivery options for an input database item.

        :arg db_item: the database record model that has the delivery options
        :type db_item: pyoseo.models.CustomizableItem
        :return: A pyxb object with the delivery options
        """

        try:
            do = db_item.selected_delivery_option
            dot = oseo.DeliveryOptionsType()
            try:
                oda = do.group_delivery_option.delivery_option.onlinedataaccess
                dot.onlineDataAccess = pyxb.BIND()
                dot.onlineDataAccess.protocol = oda.protocol
            except ObjectDoesNotExist:
                try:
                    odd = do.group_delivery_option.delivery_option.onlinedatadelivery
                    dot.onlineDataDelivery = pyxb.BIND()
                    dot.onlineDataDelivery.protocol = odd.protocol
                except ObjectDoesNotExist:
                    md = do.group_delivery_option.delivery_option.mediadelivery
                    dot.mediaDelivery = pyxb.BIND()
                    dot.mediaDelivery.packageMedium = md.package_medium
                    dot.mediaDelivery.shippingInstructions = self._n(
                            md.shipping_instructions)
            dot.numberOfCopies = self._n(do.copies)
            dot.productAnnotation = self._n(do.annotation)
            dot.specialInstructions = self._n(do.special_instructions)
        except ObjectDoesNotExist:
            dot = None
        return dot

    def _get_order_type(self, order_specification):
        """
        Return the order type for the input order specification.

        Usually the order type can be extracted directly from the order
        specification, as the OSEO standard defines only PRODUCT ORDER,
        SUBSCRIPTION ORDER and TASKING ORDER. We are adding a fourth type,
        MASSIVE ORDER, which is based on the existence of a special reference
        on orders of type PRODUCT ORDER.

        :param order_specification:
        :return:
        :rtype: models.OrderType
        """

        order_type = order_specification.orderType
        result = models.OrderType.objects.get(name=order_type)
        if order_type == models.OrderType.PRODUCT_ORDER:
            ref = self._c(order_specification.orderReference)
            massive_reference = getattr(
                django_settings,
                'OSEOSERVER_MASSIVE_ORDER_REFERENCE',
                None
            )
            if massive_reference is not None and ref == massive_reference:
                result = models.OrderType.objects.get(name=massive_reference)
        return result

    def _order_type_enabled(self, order_type):
        """
        Return a boolean indicating if the specified order type is enabled in
        the settings.
        """
        order_type_enabled = models.OrderType.objects.filter(name=order_type)
        return True if len(order_type_enabled) > 0 else False

    def _option_enabled(self, option, customizable_item):
        """
        Return a boolean indicating if the specified option is enabled.
        """

        result = False
        for group_option in customizable_item.option_group.groupoption_set.all():
            op = group_option.option
            if op.name == option:
                for op_order_type in op.optionordertype_set.all():
                    try:
                        t = customizable_item.order.order_type
                    except customizable_item.DoesNotExist:
                        # the input customizable_item is probably an order item
                        t = customizable_item.orderitem.batch.order.order_type
                    if op_order_type.order_type == t:
                        result = True
        return result

    def _c(self, value):
        """
        Convert between a None and an empty string.

        This function translates pyxb's empty elements, which are stored as
        None into django's empty values, which are stored as an empty string.
        """

        return '' if value is None else str(value)

    def _n(self, value):
        """
        Convert between an empty string and a None

        This function is translates django's empty elements, which are stored
        as empty strings into pyxb empty elements, which are stored as None.
        """

        return None if value == '' else value
