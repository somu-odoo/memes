/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { session } from "@web/session";
import { sprintf } from '@web/core/utils/strings';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #check-pincode': '_onClickCheckPincode',
        'input #pincode': '_onChangePincode',
    }),

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
        this.session = session;
        if (this.session.user_id) { 
            localStorage.setItem('odoo-userId', this.session.user_id);
        } else {
            localStorage.removeItem('odoo-userId');
            localStorage.removeItem('odoo-cart');
        }
    },

    _onChangePincode: function (ev) {
        const checkButton = document.querySelector('#check-pincode');
        if (ev.target.value.trim()) {
            checkButton.disabled = false;
        } else {
            checkButton.disabled = true;
        }
    },

    _onClickCheckPincode: async function (ev) {
        const pincode = document.querySelector('#pincode').value;
        localStorage.setItem("odoo-pincode",pincode)
        const product_template_id = document.querySelector('input[type="hidden"][name="product_template_id"]').value;
        if(this.session.user_id) {
            localStorage.setItem('odoo-userId', this.session.user_id);
            const product = await this.orm.searchRead(
                'product.template', 
                [['id','in', [parseInt(product_template_id)]]],
                ['public_categ_ids'],
                { limit: 1 }  
            )
            const product_public_categ_ids = product[0].public_categ_ids;
            let categories = [];
            if (product_public_categ_ids.length > 0) {
                categories = await this.orm.searchRead(
                    'product.public.category',
                    [['id', 'in', product_public_categ_ids]],
                    ['name','x_supported_pincodes']
                );
            
                if(categories.length > 0) {
                    const pincodes_data = await this.orm.searchRead(
                        'x_ecom.pincode', 
                        [['id', 'in', categories.flatMap(category => category.x_supported_pincodes)]],
                        ['display_name']
                    );
                    const allSupportedPincodes = pincodes_data.map(pincode => pincode.display_name);
                    if (allSupportedPincodes.includes(pincode)) {
                        document.querySelector('#pincode-result').innerHTML = "Product is available!";
                        document.querySelector('#pincode-result').style.color = "green";

                    } else {
                        document.querySelector('#pincode-result').innerHTML = "Sorry, pincode is out of service!";
                        document.querySelector('#pincode-result').style.color = "red";
                    }
                } else {
                    document.querySelector('#pincode-result').innerHTML = "";
                }
            } else {
                document.querySelector('#pincode-result').innerHTML = "Availability may vary!";
                document.querySelector('#pincode-result').style.color = "orange";
            }
        } else {
            document.location = sprintf('/web/login?redirect=%s', encodeURIComponent(window.location.pathname));
        }
    },

    _onClickAddOriginal: function (ev) {
        ev.preventDefault();
        var def = () => {
            this.getCartHandlerOptions(ev);
            return this._handleAdd($(ev.currentTarget).closest('form'));
        };
        if ($('.js_add_cart_variants').children().length) {
            return this._getCombinationInfo(ev).then(() => {
                return !$(ev.target).closest('.js_product').hasClass("css_not_available") ? def() : Promise.resolve();
            });
        }
        return def();
    },

    _onClickAdd: async function (ev) {
        ev.preventDefault()
        if(!this.session.user_id) {
            return document.location = sprintf('/web/login?redirect=%s', encodeURIComponent(window.location.pathname));
        }
        const originCartDataRaw = localStorage.getItem('odoo-cart') || '[]';
        const originCartData = JSON.parse(originCartDataRaw) || [];
        const product_template_id = document.querySelector('input[type="hidden"][name="product_template_id"]').value;
        const product_id = document.querySelector('input[type="hidden"][name="product_id"]').value;

        const productTemplateId = await this.orm.searchRead(
            'product.template', 
            [['id','in', [parseInt(product_template_id)]]],
            ['public_categ_ids'],
            { limit: 1 }
        );
        const productPublicCategIds = productTemplateId[0].public_categ_ids || null;
        const existingCategId = originCartData.map(item => item.product_public_categ_ids).flat().filter(a => a);
        if (existingCategId.length == 0 || existingCategId.includes(productPublicCategIds[0]) || productPublicCategIds[0] == null) {
            const ndata = [
                ...originCartData,
                {
                    'product_id': parseInt(product_id), 
                    'product_template_id': parseInt(product_template_id), 
                    'product_public_categ_ids': productPublicCategIds[0]  || null,
                }
            ];
            const newData = Array.from(new Map(ndata.map(item => [item.product_id, item])).values());
            localStorage.setItem('odoo-cart',JSON.stringify(newData))
            this._onClickAddOriginal(ev)
        } else {
            this.notification.add(
                'Oops! Can\'t add to cart!\n Please check your cart items, only one vendor is allowed at a time!', 
                {
                    title: "Cart",
                    type: 'warning',
                }
            );
        }
    }
});
