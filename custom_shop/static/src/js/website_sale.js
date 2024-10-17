/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #check-pincode': '_onClickCheckPincode',
        'input #pincode': '_onChangePincode',
    }),

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
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
        const product_template_id = document.querySelector('input[type="hidden"][name="product_template_id"]').value;
        const test = await this.orm.webSearchRead('product.template', [['id','=', [parseInt(product_template_id)]]],{});
        debugger
        const product = await this.orm.searchRead(
            'product.template', 
            [['id','=', [parseInt(product_template_id)]]],
            ['public_categ_ids']
        )
        
        const product_public_categ_ids = product[0].public_categ_ids;
        
        let categories;
        if (product_public_categ_ids.length > 0) {
            categories = await this.orm.searchRead(
                'product.public.category',
                [['id', 'in', product_public_categ_ids]],
                ['name','x_supported_pincodes']
            );
        }
        if(categories.length > 0) {
            const pincodes_data = await this.orm.searchRead(
                'x_ecom.pincode', 
                [['id', 'in', categories.flatMap(category => category.x_supported_pincodes)]],
                ['display_name']
            );
            const allSupportedPincodes = pincodes_data.map(pincode => pincode.display_name);
            if (allSupportedPincodes.includes(pincode)) {
                console.log("Pincode is supported!");
                document.querySelector('#pincode-result').innerHTML = "Pincode is supported!";
            } else {
                document.querySelector('#pincode-result').innerHTML = "Pincode is not supported!";
            }
        } else {
            document.querySelector('#pincode-result').innerHTML = "";
        }
    },

    async _onClickAdd(ev) {
        const product_template_id = document.querySelector('input[type="hidden"][name="product_template_id"]').value;
        this._super(ev);
    }
});
